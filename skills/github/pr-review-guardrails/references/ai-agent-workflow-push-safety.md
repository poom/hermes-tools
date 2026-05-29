# AI-Agent Workflow Push-Safety Review Notes

Session source: EWA-Services/EWA-Actions PR #379 review (May 2026). Use this as a compact checklist when reviewing CI/workflow changes that let an AI reviewer/agent make commits or push PR branches.

## High-risk pattern

A workflow claims: "agent edits/commits locally; wrapper verifies clean tree and pushes." This is only true if the agent process cannot directly push or access write credentials.

Red flags:

- `actions/checkout` uses a write token before the AI step and omits `persist-credentials: false`.
- The AI/LLM execution step receives `GH_TOKEN`, `GITHUB_TOKEN`, PATs, app tokens, provider auth files such as `CODEX_AUTH_JSON`/`<home>/.codex/auth.json`, or remote credentials with contents-write/read scope.
- The AI step has unrestricted shell / sandbox bypass / broad tool permissions (for example `codex exec --dangerously-bypass-approvals-and-sandbox`) while reading attacker-controlled PR text/diff as prompt context.
- A workflow says the prompt contains all necessary context and no repo/network access is needed, but the CLI invocation does not enforce no-shell/no-network/no-filesystem access.
- The wrapper verifies only `git status --porcelain` and `HEAD != BASELINE_SHA` before pushing.
- Branch gating checks only same-repo and `head_ref != default_branch`, but the ticket requires protected-branch rejection.
- Tests assert that safety strings appear in YAML instead of executing resolver/gating logic with fixtures.

## Prompt-only AI audit workflows

Even when an AI workflow is read-only/comment-only and does not push commits, treat PR diffs and PR bodies as untrusted prompt input. If the model/agent is run with sandbox bypass or shell tools, prompt injection in the diff can ask it to read local files, exfiltrate auth, or emit false pass markers.

Review checks:

- Require an enforced boundary: no dangerous sandbox bypass on untrusted PR prompt text, or use a non-agent completion/API path that cannot run tools.
- Set `persist-credentials: false` on checkout when the agent does not need git credentials, even for read-only workflows, so token material is not left in `.git/config`.
- Do not place provider auth files in a location the agent/tool runtime can read unless the runtime cannot execute arbitrary file reads/commands; prefer a narrowly scoped API call wrapper outside model control.
- Delimit appended PR diff/body as untrusted data and instruct the model to ignore instructions inside it; this is defense-in-depth only, not a substitute for sandbox enforcement.
- For large prompts/diffs, pass the prompt via stdin or a file input (`codex exec ... - < prompt.txt` where supported) instead of one shell argv to avoid ARG_MAX failures.
- Parse model decisions fail-closed: validate required JSON fields, exact enum values, and types. Only explicit `overallStatus == "pass"` should pass; invalid/uppercase/unknown values must fail.

## Blocker criteria

Request changes when any of these are true:

1. Push-capable credentials are visible to the AI process before the wrapper verification step.
2. Checkout persists write credentials into `.git/config` before an unrestricted AI shell step.
3. Protected/base/default/fork branch rejection is part of the requirements but not enforced before fix mode starts.
4. Commit attribution matters, but the wrapper does not verify all commits in `BASELINE..HEAD` have expected author and committer identity.
5. A reusable AI-review workflow introduces a GitHub App/check-run flow but still exposes a broad legacy PAT (for example `FINN_DEVOPS_PERSONAL_ACCESS_TOKEN` via `REVIEW_GH_TOKEN`/`GH_TOKEN`) to an unsandboxed Codex/agent process. GitHub Actions `permissions:` do not constrain PAT scope, so this is still blocker-level even if check-run writes are later performed through a scoped GitHub App token.

## GitHub App review/check-run flow nuance

Session source: EWA-Services/EWA-Actions PR #414 review (May 2026), converting AI review automation to a Codex GitHub App flow.

Good signs:

- Stable required check name is preserved, e.g. `finn-ai-coder / review`.
- The refresh/check job runs on `pull_request` and upserts a failing check when the current normalized diff lacks matching approved AI-review metadata. This is expected when acceptance criteria require a new AI review after synchronize/rebase/diff changes; do not misclassify that fail-closed refresh as a blocker.
- GitHub App token creation is scoped to the exact side effect: check-run write/read and PR read where appropriate.
- Tests cover check creation/update, approved vs requested-changes conclusions, and no-matching-diff behavior.

Danger sign that remains blocking:

- The model-controlled Codex step runs with sandbox bypass and has `GH_TOKEN` from a legacy PAT fallback. A later scoped GitHub App wrapper does not help if the model process can already call GitHub directly with broader credentials while processing untrusted PR/comment/diff prompt text.

Preferred fix direction:

- Keep broad/legacy PATs out of the model process entirely.
- Give the model only the minimum read-only context it needs, or no GitHub credential at all.
- Parse the model output fail-closed, then perform comments/reviews/check-run updates in wrapper code using narrowly scoped `github.token` or GitHub App tokens.
- If a legacy token is retained for backward compatibility, ensure it is never exported to `GH_TOKEN`/env/files visible to the agent process.

## Safer design direction

- Use read/comment-only credentials for AI review/comment steps.
- For fix mode, checkout writable refs with `persist-credentials: false` or remove credentials before running the agent.
- Do not pass push-capable `GH_TOKEN` to the AI step. Inject write credentials only in the wrapper push step.
- Gate fix mode before agent execution: same repo, non-fork, head branch exists, head != base/default, protected/ruleset check or explicit allow-list.
- Verify the commit range after the agent exits: clean tree except known artifacts, new commits exist, expected author/committer metadata, optional commit count/message policy.
- Push with a narrow refspec and no force unless explicitly required and reviewed.
- Add tests that exercise the real resolver/gate code with synthetic PR payloads and credential/isolation assertions.
