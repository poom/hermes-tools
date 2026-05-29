---
name: pr-review-guardrails
description: Use when reviewing GitHub pull requests with strict clean-code, SOLID, feature-flag, experiment-outcome, Terraform-plan, coverage, CI, missing-review-decision recovery, and GitHub posting guardrails; runs dual reviewers with GPT-5.5 plus direct Claude CLI and routes results back to the originating Discord thread or Telegram topic.
version: 1.0.0
license: MIT
required-skills: []
required-binaries: [gh, git, python3, claude]
required-env: []
required-mcps: []
metadata: github-pr-review-guardrails
---

# PR Review Guardrails

## Overview

Use this skill for thorough PR reviews where the user cares about merge safety, clean code, SOLID design, feature-flag behavior, experiment rollout/removal correctness, Terraform plan safety, and concrete review delivery.

Reference playbooks include:
- `references/terraform-googleworkspace-aliases-vs-emails.md` — Terraform Google Workspace reviews: distinguish alias/no-type `emails` cleanup from real alias deletion by checking provider behavior, module alias inputs, and the plan's final alias set.
- `references/github-actions-action-pinning-policy.md` — GitHub Actions reviews: detect repo-owned action SHA pinning policies, run the pin-check script on changed workflow/action files, and treat mutable external action refs as blocking unless the policy is intentionally updated.
- `references/github-actions-docker-production-promotion.md` — GitHub Actions reviews: when a PR adds optional Docker image build/deploy beside legacy npm deploy, verify the manual production deploy path mirrors the same selection logic and performs Docker deploy-only promotion instead of always dispatching the legacy npm-package event.
- `references/release-please-current-main-conflict-check.md` — Release Please PRs: verify live current-main mergeability and stale `.release-please-manifest.json` root versions even when tests and independent reviewers pass.
- `references/terraform-digger-wif-bootstrap.md` — Terraform/Digger WIF bootstrap reviews: verify latest plan counts, import/adoption safety, WIF provider/environment alignment, target-project bootstrap authority, and resolve stale outdated review threads after confirming fixes.

This is migrated from the OpenClaw `pr-review-guardrails` skill and adapted for Hermes:

- Reviewer A is the GPT/OpenAI Codex lane and must use GPT-5.5 semantics.
- Reviewer B is direct Claude CLI (`claude -p ...`), not ACP.
- Results must be delivered visibly back to the user, preferably in the same Discord thread or Telegram topic as the request.
- OpenClaw workspace assumptions are replaced with Hermes paths and tools.

## When to Use

Use when the user says things like:

- "Review this PR with feature-flag safety"
- "Check if this experiment integration is correct"
- "Do a SOLID / clean-code PR review"
- "Re-review PR #123"
- "Approve/request changes on this PR if safe"

Do not use for quick one-file code snippets unless the user explicitly asks for the full guardrail review.

## Execution Mode

### Mandatory dual-review lanes

Run two independent review lanes when practical:

1. **Reviewer A — GPT-5.5 / OpenAI Codex lane**
   - Prefer a Hermes subagent/delegated reviewer running with the active OpenAI Codex provider/model.
   - Expected model: `openai-codex/gpt-5.5` or provider `openai-codex` with model/default `gpt-5.5`.
   - If the Hermes/ChatGPT delegated Reviewer A lane errors, interrupts, or returns no usable structured result, try the standalone Codex CLI via PTY/rmux as a bounded fallback before marking Reviewer A unavailable. Keep it report-only (no GitHub posting, no platform messages, no edits), run inside the checked-out repo, capture output to a durable file, and synthesize only after the parent verifies the output is substantive and current-head scoped. See `references/codex-rmux-reviewer-a-fallback.md`.
   - If using the standalone Codex CLI, use the Codex skill patterns and make the model selection explicit when the CLI supports it.
   - Scheduled/rmux Codex lane pitfall: some ChatGPT-backed Codex CLI accounts reject newer Codex-family model IDs (for example `gpt-5.1-codex-max`) with `model is not supported when using Codex with a ChatGPT account`, while `--model gpt-5.5` works. On this error, relaunch the reviewer lane with `codex exec --model gpt-5.5 ...` before marking Reviewer A unavailable.

2. **Reviewer B — direct Claude Code CLI lane**
   - Default interactive/scheduled-safe path: when running under rmux/tmux scheduled review mode, or when subscription-plan compatibility means print mode (`-p`) may be unavailable, run Claude Code interactively rather than using `-p`. Prefer the pending-review helper:
     ```bash
     python "${HERMES_HOME:-$HOME/.hermes}/skills/github/pending-pr-review/scripts/rmux_claude_interactive_reviewer.py" \
       --session pr-review-claude \
       --workdir "$REPO" \
       --prompt-file "$PROMPT" \
       --output-file "$ROOT/rmux/claude.out" \
       --timeout-seconds 1800
     ```
     This starts `claude --tools ''` in rmux/tmux, pastes the prompt into the TUI, captures pane output to a durable file, and waits for a completion sentinel or idle prompt. If the captured pane idles at a tool-permission prompt (for example an MCP/Notion/Drive prompt) or contains only the pasted prompt without a substantive verdict, kill the rmux/tmux session, record Reviewer B as unavailable/transport-stalled, and continue synthesis from refreshed GitHub evidence plus any completed Codex/parent review; do not wait indefinitely or treat prompt text as reviewer output.
   - For ad-hoc one-shot reviews where print mode is still available, run Claude Code directly from the host, normally placing the prompt immediately after `-p` (this host's Claude CLI can reject `claude -p --model ... '<prompt>'` with `Input must be provided either through stdin or as a prompt argument`):
     ```bash
     claude -p '<review prompt>' --model opus --max-turns 10
     ```
   - Prefer the authenticated Claude binary on this machine (`$CLAUDE_BIN` or `$HOME/.local/bin/claude` when needed).
   - Use Claude-native aliases/names such as `opus`, `sonnet`, or `claude-sonnet-4-6`.
   - Do **not** pass OpenClaw/provider-prefixed IDs such as `anthropic/claude-opus-4-6` to `claude --model`.
   - Do **not** use ACP for Claude. The Claude lane is direct CLI only.
   - If a full-repo Claude prompt exits with `Error: Reached max turns`, retry once with a higher limit (for example `--max-turns 20`). If it still reaches max turns, do not abandon Reviewer B immediately: provide a compact, evidence-rich prompt containing the relevant diff snippets, acceptance criteria, and any SDK/API facts already verified, and ask Claude to review without tools. Record this as `direct Claude CLI / opus (compact prompt)` rather than unavailable.
   - Compact Claude fallback pattern that worked on a large TypeScript/Playwright PR: write a prompt file containing PR URL/title, head/base SHA, linked-ticket acceptance criteria, local/remote checks already verified, diff stat, and the full or curated diff; explicitly say `DO NOT use tools`; run `claude -p "$(cat /tmp/prompt.txt)" --model opus --max-turns 1`. This can succeed after tool-using Claude runs hit max-turns 10 and 20. If the compact one-turn run itself exits with `Error: Reached max turns (1)`, retry the same compact prompt with a normal small allowance such as `--max-turns 10` before marking Reviewer B unavailable; simple docs-only reviews have required more than one turn even without tools.
   - For docs-only or otherwise compact/evidence-only PRs where Reviewer B should not use tools, pass an explicit empty tool set when supported and redirect stdin from `/dev/null`: `claude -p "$(cat /tmp/prompt.txt)" --model opus --max-turns 5 --tools '' < /dev/null`. The stdin redirect avoids Claude CLI's slow-stdin warning (`no stdin data received in 3s`) when using `-p` with no piped input. This avoids accidental repo/tool exploration while still giving an independent reasoning lane over the evidence you provide.
   - Do **not** fallback Reviewer B to a Codex lane. If Claude CLI is unavailable, mark `Reviewer B: unavailable` and proceed with Reviewer A.

Run both lanes in parallel when practical. Synthesize findings after both complete:

- Blockers from either reviewer are blockers.
- Verdict is the stricter of the two.
- Conflicting non-blocker findings can be noted without escalating unless evidence warrants it.
- Limit peer-review debate to 2 rounds; then report uncertainty clearly.

### Main-context minimization

Keep the main session small:

1. Do not paste long raw reviewer output into chat.
2. Extract only: verdict, blockers, top 3 high-priority issues, merge readiness, GitHub action, and internal token usage summary.
3. For stacked PR requests, return one compact row per PR.
4. If the user asks for GitHub comments, post the detailed comments on GitHub and keep chat concise.
5. In delegated/parent-orchestrated review mode, honor instructions like `do not send chat messages` as **no platform delivery / no Discord thread messages / no Telegram messages / no GitHub posting** from the reviewer lane. Still return the requested structured result to the caller, including the proposed formal GitHub body/action for the parent to post after final head verification.
5. If the user asks a subagent/delegate to review but says **do not post to GitHub** and **do not send chat messages**, treat the task as parent-return-only: make no progress chatter, post nothing externally, and return one concise structured review plus a proposed formal GitHub review body/action for the parent to post after its own final head verification.

### Internal per-PR token usage reporting

For Poom's PR-review workflow, include a token-usage line in every user-facing per-PR result when the data is available. This is **internal-only reporting** for Discord/Telegram/chat/review-memory; do **not** include token usage in GitHub review bodies, GitHub top-level comments, or GitHub inline comments unless the user explicitly asks.

- Scope token usage to the PR review when practical: Reviewer A lane, Reviewer B lane, parent/orchestrator synthesis, and total.
- Prefer exact usage emitted by the reviewer tool or saved run metadata. If exact counts are unavailable, show `unavailable` rather than guessing.
- Accept compact approximations only when clearly labeled, for example `Token usage: A 120k, B unavailable, parent ~18k, total ~138k`.
- If a reviewer lane writes logs/output files, preserve any usage footer/metadata in the PR review artifact and extract the numbers for the chat summary.
- Token usage is informational and must not affect approve/request-changes decisions.

## Result Routing: Discord Channels / Threads and Telegram Topics

The final PR result must be visible in chat, not only stored in files or posted to GitHub.

Preferred routing:

2. **Discord**
   - Default for Poom's PR-review workflow: **one PR = one normal Discord text channel under the `review-prs` category**, with a deterministic reusable channel name `<repo-name>-pr-<pr-number>` (lowercase/hyphen Discord-safe form, for example `finn-web-app-pr-4974`). This is preferred over creating public threads in the parent request channel because normal channels show in the left sidebar and can be reused across repeat asks.
   - If the request is already inside the correct PR-specific normal channel, continue there.
   - If the request is in a normal parent channel/thread such as `#review-prs`, create or reuse the PR-specific normal channel under category `review-prs` before sending progress/final PR-review output. Do **not** rely on Hermes auto-threading for this workflow unless the user explicitly asks to keep the review in the current thread/channel or channel creation fails.
   - Channel name: `<repo-name>-pr-<pr-number>`; channel topic: `<Owner>/<Repo> #<number> — <PR URL> — managed by Hermes pr-review-guardrails`.
   - Reuse/adopt an existing channel for the same PR; never create duplicate lanes for repeat asks.
   - Prefer the existing normal-channel helper from `my-open-prs` until this skill has its own helper:
     ```bash
     set -a; . "${HERMES_HOME:-$HOME/.hermes}/.env"; set +a
     python "${HERMES_HOME:-$HOME/.hermes}/skills/github/my-open-prs/scripts/discord_pr_channels.py" create \
       --source-channel-id "$SOURCE_CHANNEL_ID" \
       --name "<repo-name>-pr-<pr-number>" \
       --category-name "review-prs"
     # JSON output contains channel_id. Send future progress/result messages to:
     #   discord:<channel_id>
     ```
   - When a channel ID is known, send the per-PR final summary to `discord:<channel_id>` and post a compact index/link back in the original request thread/channel if needed.
   - If normal channel creation fails because the bot lacks permissions or `DISCORD_BOT_TOKEN` is unavailable, fall back to the origin thread/channel, include the full PR URL, and explicitly mention the channel-creation limitation.
   - If the current review lane is already a Discord thread because an older run created one, do not abandon the user-visible result. Finish there, but for future/repeat asks create or reuse the normal PR channel under `review-prs` unless the user says otherwise.
   - Status values in messages should be review/verdict-oriented, not raw merge-state oriented:
     - `Reviewing` while the review is in progress or no final verdict is posted.
     - `Approved` after a formal approval / approve-level verdict.
     - `Requested changes` after a formal request-changes / needs-changes verdict.
     - `Commented` when feedback was posted without approve/request-changes.
     - Use `Approved (blocked)` only when useful to show approval is done but external merge gates are still blocking.
If the current review lane is a Discord thread whose name does not match the current lifecycle state, rename it promptly only when continuing in that legacy thread is intentional. Prefer first-class Discord/admin tooling if available; otherwise use this skill's helper script when the bot token is available:
     ```bash
     python "$HOME/.hermes/skills/github/pr-review-guardrails/scripts/discord_rename_thread.py" \
       env:DISCORD_BOT_TOKEN \
       "$THREAD_ID" \
       "EWA-Actions #380 - Approved"
     ```
     The helper accepts exactly `TOKEN THREAD_ID NEW_NAME`; `TOKEN` may be raw, `env:VAR_NAME`, or `@/path/to/token_file`. It sets the correct DiscordBot `User-Agent` header and never prints the token. If `env:DISCORD_BOT_TOKEN` is missing in the process environment, check `${HERMES_HOME:-$HOME/.hermes}/.env` without printing secrets and source it for the helper call:
     ```bash
     set -a; . "${HERMES_HOME:-$HOME/.hermes}/.env"; set +a
     python "$HOME/.hermes/skills/github/pr-review-guardrails/scripts/discord_rename_thread.py" \
       env:DISCORD_BOT_TOKEN "$THREAD_ID" "EWA-Actions #380 - Approved"
     ```
     If the API still returns 403 with a valid User-Agent and JSON Discord error body, report that the bot lacks permission to manage the thread; if the token/tooling is unavailable, mention the limitation briefly in the final summary rather than pretending it was renamed.

2. **Telegram**
   - If the request is inside a Telegram forum topic, reply in the same topic (`telegram:<chat_id>:<message_thread_id>` when using explicit delivery).
   - One PR review should map to one Telegram topic when feasible. If topic creation is not available from the current toolset, ask the user to start the request inside the desired topic or use the current topic as the review lane.
   - Do not fan results into the parent group when a topic/thread context exists.

3. **Other contexts**
   - Reply to the origin conversation.
   - If a background/detached reviewer completes without a visible structured summary reaching the user, treat it as delivery failure and resend the summary explicitly.

For long reviews, send a brief progress note only if work will continue for several minutes; otherwise avoid noisy updates.

### Auto-close review threads on approval

When the synthesized verdict is **Approve** / merge-ready and there are no blockers or unresolved follow-ups requiring user attention:

1. Deliver the final chat summary first.
2. Complete any user-authorized GitHub action (formal approval/comment) before closing the chat lane.
3. If the current platform/toolset supports thread/topic closure or archiving, close/archive only the dedicated PR review thread/topic after the final summary is visible.
4. Never close a parent channel/group or an unrelated shared thread.
5. If thread closure is not available from the current Hermes platform tools, say so briefly in the final summary instead of pretending it was closed.

Do **not** auto-close when the verdict is Needs changes / Blocked, when GitHub posting is still pending, when background reviewers are still running, or when the user asked to keep the review thread open.

## Review Setup

- Use one dedicated worktree per PR:
  - Preferred: `<workspace>/repo/<repo-name>-<pr-number>`
  - Avoid creating PR review worktrees directly in a workspace root.
- Session/task labels must include repo slug and PR number; never use plain `pr<number>` labels because they collide across repos.
  - Pattern: `<repo-name>-pr-<pr-number>`
- Fetch PR diff, title, body, comments, checks, review state, and linked ticket/experiment context.
- Use `gh` for GitHub metadata when available.
- Use `linear` for linked Linear ticket details when a ticket is referenced.
- When using a bare clone plus worktree, confirm which base ref name exists in the worktree before diffing. `git fetch origin "$BASE" +pull/N/head:refs/remotes/origin/pr-N` may leave a local `master`/`main` branch available but no `refs/remotes/origin/$BASE`; if `git diff origin/$BASE...HEAD` is ambiguous, use the verified local base ref (`git rev-parse refs/heads/$BASE`) or fetch explicitly with `git fetch origin "$BASE:refs/remotes/origin/$BASE"` before retrying.

## Freshness Check

See also `references/github-review-verification-quirks.md` for verifying a newly posted formal review when `gh pr view --json latestReviews` or `reviewDecision` appears stale because of unresolved human/policy gates.

See also `references/python-poetry-unavailable-test-fallback.md` for narrow Python unit-test fallback patterns when Poetry is unavailable and a full dependency environment is impractical.

Before every review or re-review, refresh the live PR state from GitHub. Never rely only on local assumptions or prior comments. For volatile/actively rebased PRs, also use `references/volatile-pr-heads.md` for force-fetch and double-check patterns.

Minimum freshness checklist:

1. Current head SHA
2. Current changed files and live diff
3. Current PR title and body
4. Current checks / reviewDecision / merge state
5. New review comments or author replies since the last pass
6. Prior formal reviews and inline review threads, including author replies and other reviewers' later decisions

GitHub CLI quirk: `gh pr view --json reviewThreads` is not available in some installed `gh` versions even though review threads are required evidence. When it fails with `Unknown JSON field: "reviewThreads"`, use GraphQL instead of skipping thread review. Query `repository { pullRequest(number:N) { reviewThreads(first:100) { nodes { isResolved comments(first:20) { nodes { author { login } body path line originalLine createdAt outdated } } } } } } }` and record total/unresolved counts plus any unresolved or author-replied blocker threads in the evidence packet. See [`references/github-review-threads-graphql-fallback.md`](references/github-review-threads-graphql-fallback.md) for a copyable command and pagination pitfalls. If `gh api graphql -f query=@query.graphql` fails by sending the literal `@...` as the GraphQL document (for example `Expected one of SCHEMA... actual: DIR_SIGN ("@")`), retry with `-f query="$(cat query.graphql)"` or another explicit file-read substitution rather than abandoning thread review.

Rules:

- Review the current head only.
- Treat author replies and other reviewers' comments as first-class review evidence, not background noise. Read them before deciding whether a prior finding remains valid.
- For every prior blocker / requested-change thread, build a short thread ledger before repeating it:
  1. Original finding: what was claimed, where, and on which commit/head.
  2. Author response(s): quote or summarize the latest relevant author reply, including any scope/product/analytics rationale.
  3. Current-code evidence: whether the current head implements the requested fix, implements an alternate fix, intentionally does not implement it, or makes the finding stale.
  4. Decision: whether to keep blocking, downgrade to non-blocking follow-up, ask for clarification, or mark resolved/stale.
- Classify author replies explicitly when they affect the decision:
  - **Clear + credible**: the reply gives a concrete rationale or alternate contract, matches the ticket/product context, and current code evidence supports it. Do not repeat the old request-changes verbatim; approve or downgrade unless a separate technical blocker remains.
  - **Clear but unimplemented**: the reply agrees with the issue or promises a fix, but current head does not contain the fix. Keep/request changes and cite the missing implementation.
  - **Unclear / needs clarification**: the reply is ambiguous, omits the contract/owner/risk acceptance needed to decide, or conflicts with the ticket. Ask a targeted clarification question instead of guessing.
  - **Disagreement needing evidence check**: the author disputes the finding or says it is intentional. Verify against code, tests, ticket/experiment/product context, and relevant external evidence. Keep blocking only if evidence still shows a concrete merge risk; otherwise record the rationale and downgrade/approve.
- If a prior finding was based on an older branch state, re-validate it before repeating it.
- Before posting `APPROVE` or `REQUEST_CHANGES`, confirm the finding still exists on the current head.
- If the current diff no longer contains a previously flagged change, mark that prior finding stale or resolved.
- If review memory proves a full prior guardrail approval on an older head and the live head only adds a narrow post-approval delta, do not blindly redo the whole XXL review or duplicate stale approvals. Use `references/current-head-approval-after-small-delta.md`: verify the missing current-head Poom approval through the pulls reviews API, inspect `OLD_HEAD..HEAD`, re-read live threads/comments, run focused validation plus a compact direct Claude CLI Reviewer B prompt over the delta, resolve any stale fixed threads, then post and verify a full current-head formal review. For docs-only IAM/permission-grant follow-ups, also use `references/docs-only-iam-grant-delta-after-approval.md` to cross-check that documented grants match runtime/deploy paths and preserve least privilege.
- For long reviews or dual-review runs, refresh the PR again immediately before synthesis. If the head SHA changed while reviewers were running, update the local checkout to the new head and re-run or narrowly re-validate the affected findings against the new diff before finalizing. Do not summarize stale reviewer output as current. See `references/rebase-force-push-during-review.md` for the rebase/force-push pattern where `OLD_HEAD..NEW_HEAD` can show unrelated base-refresh files even though the live PR-owned `base...HEAD` diff is unchanged.
- For stacked or stale PRs where `mergeStateStatus` is `DIRTY`/`BEHIND` and `base...HEAD`/`main..HEAD` includes noisy adjacent-stack files, use `references/stacked-stale-pr-diff-noise.md`: build a PR-owned scope ledger from title/body/specs, prior threads, and current-head implementation; verify old blockers against current code/tests; treat stale/dirty merge state as process unless the PR-owned shared contract is actually broken; and make any approval explicitly current-head-scoped with a re-check note after rebase/update.
- Immediately before posting a formal GitHub review, fetch the head SHA again. On volatile PRs, sample it twice with a short delay; abort posting if it changed, refresh, and revalidate instead of posting a stale approval/request-changes.
- Always diff against the PR's actual `baseRefName` from `gh pr view`, not a hardcoded branch. Fetch that base explicitly before local diffs. Prefer a fully qualified source ref, especially in disposable `gh repo clone --no-checkout` checkouts where `origin/<base>` may be dangling/deleted until fetched:
  ```bash
  BASE=$(gh pr view N --json baseRefName --jq .baseRefName)
  git fetch origin "+refs/heads/$BASE:refs/remotes/origin/$BASE" \
    +pull/N/head:refs/remotes/origin/pr-N
  git diff --stat "origin/$BASE...HEAD"
  ```
  If `git diff origin/$BASE...HEAD` is still ambiguous, run `git show-ref | grep "refs/remotes/origin/$BASE"` and re-fetch using `+refs/heads/$BASE:refs/remotes/origin/$BASE` before reviewing the diff. Avoid `origin/master...HEAD` unless the PR base is actually `master`; many repos use `main`, and the wrong base can produce a huge misleading diff/stat.
- If the author force-pushes/rebases and `git fetch origin pull/N/head:refs/remotes/origin/pr-N` fails with `non-fast-forward`, use a leading `+` refspec for the disposable review ref with the real base branch: `git fetch origin "$BASE" +pull/N/head:refs/remotes/origin/pr-N`.
- If the head changes between synthesis and posting, do not post the stale verdict. Fetch/reset to the new PR head, inspect `OLD_HEAD..NEW_HEAD` plus the live `base...HEAD` diff, and specifically check whether your blocker was fixed. If the blocker is resolved with an appropriate regression test, switch to a re-review/approve-level body rather than submitting the old request-changes review. See `references/head-changed-after-drafting-review.md` for the concrete pattern where a Ruff-format blocker was fixed after the request-changes body was drafted but before posting. If the head changes in a scheduled/batch run when tool budget is nearly exhausted, use `references/head-changed-request-changes-cutoff.md`: abort the stale post, do not recycle old inline comments, and report the PR as still pending unless the new head is fully revalidated and posted.

## Ticket Discovery

Before reviewing, identify the related ticket from PR metadata in this order:

1. PR description
2. PR title
3. PR comments

Use:

- `gh` to read PR title/body/comments/checks.
- `linear` to fetch ticket details, acceptance criteria, and experiment context.
- Prefer the Linear CLI or this skill's helper over ad-hoc `curl | python` / custom GraphQL Python snippets. In Hermes sessions, those ad-hoc pipelines can trigger approval prompts repeatedly. Approved patterns:
  ```bash
  # Plain CLI; good when raw JSON is enough.
  set -a; . "${HERMES_HOME:-$HOME/.hermes}/.env"; set +a
  linear issue view DEV-2641 --json --no-pager --no-download > /tmp/linear-DEV-2641.json

  # Helper; loads ~/.hermes/.env, calls linear CLI, and emits prompt-ready Markdown.
  python "${HERMES_HOME:-$HOME/.hermes}/skills/github/pr-review-guardrails/scripts/linear_ticket_context.py" \
    DEV-2641 > /tmp/linear-DEV-2641.md
  ```
- When multiple tickets are referenced, pass them all to the helper in one call to minimize tool churn:
  ```bash
  python "${HERMES_HOME:-$HOME/.hermes}/skills/github/pr-review-guardrails/scripts/linear_ticket_context.py" \
    DEV-2641 DEV-2642 > /tmp/linear-context.md
  ```

If no required ticket can be found for a PR that should have one, mark it as a blocker or ask the user for the ticket ID.

## Core Review Checks

### 1) Code quality and SOLID

- Clear naming, low complexity, no dead code, no duplicated logic.
- Single responsibility: avoid overloaded modules/functions.
- Open/closed: avoid brittle edits requiring repeated modification.
- Liskov/interface/dependency rules: verify contracts, focused abstractions, explicit dependencies.
- Maintainability and readability.

### 2) Feature-flag safety

If PR introduces new behavior:

- New behavior must be gated by a feature flag unless the user/repo policy explicitly says otherwise.
- Flag OFF must preserve current behavior and safety.
- Validate both paths:
  - Flag ON: new behavior works.
  - Flag OFF: old behavior remains unchanged/safe.

If a needed flag is missing, mark as blocker.

For campaign-landing PRs that add new registry entries/components behind an existing shared kill-switch guard, use [`references/campaign-landing-kill-switch-diff-only-checks.md`](references/campaign-landing-kill-switch-diff-only-checks.md): verify the unchanged route guard/service path before treating a diff-only GrowthBook implementation-check failure as a real blocker.

### 2a) Runtime configuration compatibility

When a PR removes, renames, or stops supporting environment-driven config values (exporters, providers, feature toggles, endpoints, legacy aliases), or changes runtime defaults/example envs, see also `references/runtime-config-defaults-rollout-safety.md`.

- Check whether the application still accepts the removed value via `env(...)` or equivalent dynamic selection. Removing a config target while leaving the selector open can create a runtime misconfiguration path.
- Search the repository and, when appropriate for org-wide deployment config, GitHub code search for straggler env values before deciding whether the risk is blocking or intentional cleanup, for example:
  ```bash
  gh search code 'OTEL_TRACES_EXPORTER=zipkin org:EWA-Services' --json repository,path,textMatches --limit 20
  gh search code 'OT_OTLP_HTTP_ENDPOINT org:EWA-Services' --json repository,path,textMatches --limit 50
  ```
- If an existing unresolved review thread covers the same compatibility path, treat it as first-class evidence and do not duplicate inline comments; resolve by summary review or explicit rationale.
- If the author later clarifies in the PR description/comments that a removed env value was never deployed or used, re-review rather than repeating the old blocker verbatim: verify current PR metadata, org/repo code search for the exact env/value, tests updated to match the new contract, and CI on the current head. If evidence supports the claim and no deployed-config source contradicts it, downgrade the finding from blocker to non-blocking rollout caveat. Still mention that repo code search cannot inspect live secret stores and recommend an ops/SRE sanity check before rollout.
- Treat generated/example envs as active defaults when setup scripts copy them into runtime files (`make prepare-env`, devcontainer setup, framework post-create hooks, CI bootstrap). If a PR puts a cluster-only/internal endpoint (for example `*.svc.cluster.local`) into both the app fallback and `.env.example`, verify the local/dev runtime actually provides that service. “It can be overridden by env” is not enough when the PR-generated default is unsafe.
- For telemetry/exporter migrations, check whether unreachable endpoints can block request/shutdown/worker paths through synchronous export/flush, retries, or long timeouts. If so, require a local-safe default, deployment-only endpoint configuration, or a local collector service plus tests for the default path.
- Prefer a safe transitional path when usage is uncertain: keep the old target until deployments are migrated, or explicitly normalize/reject unsupported env values with tests and a clear operator-facing migration note.

### 3) Experiment-result policy

When PR removes or integrates flag/experiment logic, require explicit experiment outcome:

- **Rollout / force rule / won**: integrate the kept/stable path.
- **Lost**: force OFF behavior, remove losing variant/new behavior, and keep control behavior.

If outcome evidence is missing, mark as blocker and request the source (Linear, GrowthBook, experiment report, etc.).

For force-rule feature-flag cleanup PRs, use `references/force-rule-feature-flag-integration-pr-case.md` as a concrete approve-level pattern: read both the force-rule ticket and original feature DoD, search for behavior-specific legacy APIs as well as flag identifiers, verify the kept path is unconditional and safe, and separate process/metadata gate noise from code blockers.

### 3a) Experiment funnel analytics preload semantics

When a PR preloads Learn/Financial Education/article content from an experiment funnel page, and comments object that the preload uses a tracked detail endpoint, separate **accepted impression attribution** from **duplicate conversion tracking**. See `references/learn-preload-impression-attribution-pr-case.md` for the concrete FINN-Web-App #4949 pattern.

- If the author/product clearly states that one tracked preload/impression is intentional for the rollout, do not keep blocking solely because the preload is tracked; treat strict click-only analytics or an untracked eligibility endpoint as a follow-up unless the ticket requires it.
- Still block if the user journey double-counts: the source page preloads through the tracked endpoint and the article-detail/open path calls the same tracked endpoint again for the same slug.
- Approve-level evidence includes a source-scoped one-time handoff/cache, article detail consuming that handoff before the tracked fallback, and tests proving the prefetched path skips the tracked request.

### 4) Test and coverage gates

For certification-only PRs whose stated purpose is to add tests/CI and lock current behavior before production changes, use `references/certification-only-test-ci-prs.md`: verify the live net `base...HEAD` diff is tests/CI only even if branch history or stale bot comments mention production-file edits, then review whether the tests intentionally certify current behavior without production drift.

- Verify tests cover changed behavior and both critical flag paths when applicable.
- Coverage must be >= 80% on changed/new code, or the repo's stricter configured gate.
- Do not force low-value test padding for straightforward migrations/entities when meaningful runtime behavior is already covered and the repo gate passes.
- If the repo's documented test runner is unavailable locally (for example `poetry: command not found`), do not stop after the first failure. Use the repo's remote CI as ground truth and, when practical, run a narrow isolated equivalent with `uv run --isolated --python <version> --with pytest --with <runtime deps> pytest <target> -q`. If `uv run --isolated` is not enough because the repo has private/git dependencies but the targeted tests only need a small import-time dependency set, use the throwaway `--target`/`PYTHONPATH` fallback in `references/python-poetry-unavailable-test-fallback.md`. If an internal/private package is not resolvable from PyPI but the tests stub it at import time, omit that package and include only import-time dependencies actually required by `conftest.py` / module import. Record the fallback command and why it differs from the repo command in the review body.
- For Python package-skeleton or `src/`-layout PRs, use `references/python-src-layout-package-prs.md`: if host pytest fails with `ModuleNotFoundError` for the package, rerun with `PYTHONPATH=<package-dir>/src` or an editable install before calling tests broken; verify `pyproject.toml` runtime metadata such as `requires-python` against stdlib imports like `zoneinfo`; and check non-fatal shared helper contracts include construction/config errors inside the guarded path. For large executable-spec + package-skeleton PRs where downstream phase specs depend on a shared runner contract, also use `references/atlas-scout-reports-package-skeleton-case.md`: compare implementation signatures to the specs landing in the same PR, require portable secret paths, account propagation, subprocess timeouts, self-contained test extras, and heartbeat URL redaction.
- If a checks list contains an old failed run plus a newer rerun/follow-up gate for the same policy, distinguish stale failures from current merge blockers. Report the stale failure as a process note only when the current replacement gate is passing. When scripting post-review check polling, remember `gh pr checks` can exit non-zero merely because an old/stale check failed; capture its output with `|| true` before grepping/counting statuses. Some installed `gh` versions also reject `gh pr checks --json conclusion` with `Unknown JSON field: "conclusion"`; use available fields such as `name,state,startedAt,completedAt,link,bucket,workflow` and map `state`/`bucket` instead of retrying unsupported schemas. For AI-label/metadata gates and duplicate check rows after label/body/comment/review-triggered reruns, use `references/process-gate-check-quirks.md`: inspect `gh run list` and failing logs with `gh run view RUN_ID --log-failed`, quote the exact validator message, and treat it as merge/process readiness unless the diff itself changes that validator. For the concrete pattern where a base/main refresh changes the head during review and stale GrowthBook/finn-ai-coder rows remain after a current-head approval, use `references/base-refresh-and-process-gate-pr-case.md`.
- When prior `CHANGES_REQUESTED` reviews or policy-bot disapprovals were about process gates (for example missing GrowthBook/no-experiment override) rather than current code correctness, re-check PR comments/checks for a later approved override before carrying the old blocker forward. If the underlying gate now passes but the old human/policy review still keeps `reviewDecision=CHANGES_REQUESTED`, an approve-level code review is appropriate; report merge readiness as `approved but blocked by process gates`, not `needs changes`.
- For failed `metadata-gate / Refresh finn-ai-coder review check` rows, use `references/finn-ai-coder-refresh-check-noise.md`: inspect the failed run log and the underlying/current `finn-ai-coder / review` body. If the refresh job merely mirrored `finn-ai-coder` failure (for example `Refreshed finn-ai-coder / review on <head>: failure (none)`) and current code/security CI plus current-head review evidence are approve-level, treat it as process/metadata noise rather than a code blocker. Similarly, when a stale `finn-ai-coder / review` row failed only because a direct CLI review job reported `Codex did not post a top-level PR response comment`, while a later/current code-review workflow and metadata refresh rows pass on the same head and a bot/human review body exists, classify it as workflow/comment-posting noise rather than a code finding. For any red `finn-ai-coder / review`/finish-check row, also use `references/finn-ai-coder-failed-check-classification.md`: inspect the bot review metadata/log before downgrading it. A wrapper failure with an approve-level substantive verdict is process noise; a current-head `REQUEST_CHANGES` verdict with a concrete finding remains review evidence to verify and carry forward or explicitly rebut.
- When a PR introduces or rewires the AI-review/metadata-gate workflows themselves, a normal `@finn-codex` issue comment may run the workflow from the base branch and be skipped or fail to exercise the PR's changed reusable-workflow caller. If the PR branch defines a `workflow_dispatch` path for the review workflow, trigger that branch ref explicitly with `gh workflow run ... --ref <pr-head-branch> -f pr_number=<N> ...` to get current-head AI-review metadata, then re-check `gh pr checks`. Treat any resulting `REQUEST_CHANGES`/failed `finn-ai-coder / review` as a real blocker even if local/manual review looked safe.
- When local language tooling is unavailable (for example no `php`/Composer/vendor on the host), do not stop at “could not run tests.” Pull failing CI logs with `gh run view <run-id> --log-failed --repo OWNER/REPO` and inspect the exact failing test/linter output. If a new/updated test encodes a prior review requirement (for example a config compatibility contract) and fails because production code violates it, treat that as evidence for the blocker rather than dismissing it as “just a red test.”
- If below threshold, request/add tests.

### 5) Paginated producer/consumer contract safety

For linked PRs where one repo adds a paginated API and another repo consumes it, review the producer/consumer contract explicitly. See `references/paginated-api-consumer-contracts.md`; for a concrete approve-level example involving a memory-safe membership-period sync, see `references/paginated-membership-period-sync-case.md`.

Key checks:

- Identify the pagination unit: flat item-level pagination can split a logical group/user/account across pages; grouped pagination must explicitly guarantee group atomicity.
- Do not treat item-level producer pagination as an AMS/API blocker merely because a consumer wants grouped behavior. If the endpoint returns flat records by design, cross-page aggregation is normally a consumer responsibility unless the ticket/API contract says otherwise.
- In the consumer, treat per-page processing as risky when it performs destructive per-group operations such as deleting/replacing child rows, overwriting subtotals, or marking a parent processed. Require aggregation/staging by the logical key across all fetched pages or idempotent merge semantics.
- Require a regression test where the same logical key appears on multiple pages and asserts all child records survive plus aggregate totals include the cross-page sum.

### 5a) Dependency automation hardening

When a PR adds or changes Dependabot, Renovate, package-update bots, or shared dependency-update templates, check supply-chain safety in addition to YAML/schema correctness. See `references/dependency-automation-hardening.md` for current Dependabot cooldown notes.

When a PR adds or changes a PolicyBot / required-review bypass for Dependabot or another automation actor, also use `references/dependabot-policybot-bypass-safety.md`. A zero-review automation bypass must still preserve required safety gates: exact bot author matching, `only_has_contributors_in`/equivalent to prevent human piggyback commits, and explicit `has_status` CI/security checks unless centralized enforcement is proven for every affected template/repo class. Inconsistent status gating across sibling shared templates is request-changes-level unless the PR provides a concrete centralized-policy mapping or rollout proof.

### 5a) GitHub Actions release-marker / version-file workflow safety

For reusable GitHub Actions workflows that parse and update production/release markers in files, use `references/github-actions-release-marker-workflows.md`. In particular, verify that exact marker matching is applied consistently to both read/lookup and write/mutation paths. A PR can fix `grep` lookups while leaving a `sed` replacement range prefix-based, so prefix-overlapping components still produce no version-file update.

### 5a) GitHub Actions workflow_dispatch tag-validation safety

For manual production deploy workflows that validate a tag input or tag ref before checkout/deploy, use `references/github-actions-workflow-dispatch-tag-validation.md`. Verify checkout uses only a validated deploy ref, private repos use authenticated API validation rather than unauthenticated pre-checkout `git ls-remote`, and branch/SHA/traversal-style inputs fail the gate on the current head.

### 5a) GitHub Actions required-checks comment / Policy Bot status surface workflows

For workflows that post or maintain a PR comment summarizing required-check status from `.policy.yml` / Policy Bot `has_status`, use `references/github-actions-required-checks-comment-workflows.md`.

### 5a) GitHub Actions issue_comment smoke tests with secrets

For secret-bearing smoke/e2e workflows (Newman/Postman, curl probes, synthetic checks) that run from PR comments on trusted or self-hosted runners, use `references/github-actions-issue-comment-secret-smoke-tests.md`. In particular, default-branch `issue_comment` execution can be safer than the ticket's temporary `pull_request` request when secrets/runners are involved, but only if the job gates by PR comment + strict slash-command + collaborator permission and never checks out PR-controlled code before using secrets.

Key checks:

- Verify the generated marker comment against live check-runs/statuses for the same head SHA; a passing workflow check is not enough if the comment content is wrong.
- Ensure workflow permissions match the APIs used (`checks: read` for check-runs, `statuses: read` for commit statuses) and non-404 API failures are not silently rendered as `missing`.
- Preserve Policy Bot semantics: honor `has_status.conclusions` instead of globally treating conclusions such as `neutral` as passing.
- Add PR/head-scoped concurrency for overlapping `pull_request`, `check_run.completed`, `check_suite.completed`, and `status` events; otherwise duplicate marker comments can be created.
- Paginate check-runs, statuses, and issue comments before concluding that a required check or existing marker comment is missing.
- For centrally synced workflow templates, compare the ticket/PR acceptance scope with sync manifest changes; if rollout/sync is deferred, make sure the PR/ticket explicitly narrows the POC scope.

### 5a) GitHub Actions / SonarCloud coverage workflow PRs

For PRs that add, remove, or consolidate SonarCloud/code-coverage workflows, use `references/sonarcloud-coverage-workflow-prs.md`. In particular, verify that workflow path filters include all test-entrypoint and report inputs (`Makefile`, requirements/lock files, `.coveragerc`, `sonar-project.properties`, workflow file, tests, and source dirs), and that `.coveragerc`, pytest/coverage flags, and Sonar source/test/report settings are aligned. Treat a local isolated test failure caused solely by unavailable private internal dependencies as an environment limitation when current-head remote CI proves the configured dependency path works; report it separately from code blockers.

### 5b) Angular / Node major-version migration PRs

For Angular/Ionic frontend major-version migrations or Node runtime upgrade PRs, use `references/angular-node-major-migration-prs.md`: compare the PR against the linked ticket/DoD, package versions, `engines.node`, CI `node-version`, lockfile engine requirements, and browser support contract. Passing CI is not enough when the PR ships Angular/Node versions below the accepted ticket scope (for example Angular 18 / Node 20 for a ticket requiring Angular 19+ / Node 22+). If `.browserslistrc` is broadened, verify existing CSS features such as `:has(...)` are supported by the newly declared browser floor or require a fallback.

### 5c) GitHub Actions version bump / SHA pinning PRs

When a PR mechanically bumps or pins GitHub Actions `uses:` references, review it as a supply-chain rollout change, not only as YAML churn:

- Confirm the diff is limited to action reference lines unless the PR explicitly claims broader workflow behavior changes.
- Verify every external action pin is a full 40-character SHA and that any trailing tag comment matches the upstream ref. A reliable check is `git ls-remote https://github.com/OWNER/REPO.git refs/tags/TAG refs/tags/TAG^{}` and compare the dereferenced result to the pinned SHA.
- Run the repo/org pin-manager check when available; if it reports internal reusable workflows/actions such as `OWNER/InternalRepo/...@main` as intentionally allowed, do not invent a blocker solely because those internal refs are not SHA-pinned.
- Parse workflow YAML locally and run whitespace/diff checks. Use `actionlint` when available, but if unavailable, record that and rely on CI plus a local YAML parse fallback. On this macOS host, `python3 -c 'import yaml'` may fail because PyYAML is not installed; Ruby's stdlib parser is a lightweight fallback: `ruby -e 'require "yaml"; p YAML.load_file(".github/workflows/name.yml").keys'`.
- For multi-major `actions/upload-artifact` / `actions/download-artifact` bumps, check artifact names are unique per matrix lane/shard and downloads use supported `pattern`/path semantics. CI logs showing successful upload/finalization are strong evidence the artifact plumbing survived the bump.
- Treat unrelated flaky test failures separately from action-plumbing failures: inspect failed-job logs enough to distinguish test assertions/timeouts from action setup/upload/download errors.

### Go CLI / single-file utility review quirks

For standalone Go command-line utilities, especially repos without `go.mod`, use `references/go-cli-review-quirks.md`. Key points: `go test ./dir` can fail only because no module exists; explicit file tests or `go test -c` compile-only may be the correct local fallback. On this macOS host, Go-built binaries may compile but abort with dyld `missing LC_UUID load command`; record that as a host execution limitation, rely on passing remote CI plus local compile/vet checks, and never claim `go run`/runtime tests passed unless they actually executed.

### PR velocity / aggregate Chat report config reviews

For GitHub PR-review SLA probe/reporter PRs that scan review requests and post Google Chat alert cards, use `references/github-pr-review-sla-alert-tools-case.md`: verify scan completeness metadata, no clean-looking truncated scans, user/team request handling, bot requestee exclusion, bounded Chat output with full logs, and workflow path-filter/test-list alignment.

For `atlas-scout-reports` consolidation/port PRs that touch shared live runner, Google Chat/Sheets delivery, heartbeat, or report readback paths, use `references/atlas-scout-reports-runtime-consolidation-case.md`. Passing report tests are not enough when the live runtime contract can still leak Chat/Sheets payloads, consume the wrong Chat response envelope, leave stale sheet rows after shrink, or wedge on unbounded external CLIs.

For small `atlas-scout-reports` follow-ups that lower the Python runtime floor and/or change shared runner timeouts, use `references/atlas-scout-reports-python-floor-timeout-followup.md`: require CI or local validation under the declared minimum Python version, keep external CLI timeouts finite/bounded, preserve sensitive-output redaction, and classify stale inline blockers about missing 3.10 CI as resolved when the current matrix covers and passes 3.10.

For Atlas Scout TA Refresh / Source Tracking PRs that change attribution from title/role matching to Greenhouse `job_id`, use `references/atlas-scout-ta-refresh-source-tracking-job-id-case.md`: explicitly probe a row with legacy `greenhouse_job_id` but no `job_id`, verify required DQ rather than silent attribution, check duplicate-title jobs split by ID, and verify linked producer/deploy sequencing separately from code blockers.

For `atlas-scout-reports` source-migration PRs that add deterministic report copies for side-by-side validation while explicitly deferring production cron/wrapper rewiring, use `references/atlas-scout-reports-source-migration-case.md`: verify runner import/help paths, changed-test subset, compile/lint/format, non-live delivery defaults, pre-send Chat gates, no introduced secrets, and classify unrelated stale full-CI collection errors as process/merge-readiness rather than current-diff code blockers.

For PRs that standardize PR-velocity, engineering-throughput, AI-signal, Supabase-backed, or Sonar-enriched Chat reports, use `references/pr-velocity-chat-config-review.md`. For PRs that add local/browser dashboards or dashboard-facing Supabase views, also use `references/pr-velocity-dashboard-views-case.md`. For follow-up fixes around Sonar filtering, roster/focus filters, and local dashboard validation, use `references/pr-velocity-sonar-roster-filter-fix-case.md`. For a concrete parent-delegated/no-posting approve-level example with ENG-964/Sonar/Supabase guardrails, see `references/pr-velocity-chat-config-tools-133-case.md`.

Key checks:

- Chat output should remain aggregate-only unless product/policy explicitly approves per-person or per-team rankings; verify renderers, tests, and config do not leak roster identities into the Chat output.
- For browser/local dashboard views, check the Supabase credential boundary: no third-party runtime scripts can read pasted keys, no `?key=` URL loading, and any browser key is proven read-only/RLS-scoped.
- Dashboard SQL/JS must derive focus scope from canonical roster/report data rather than duplicating login allowlists, and must use the same Asia/Bangkok Monday-Sunday week contract as the Go report pipeline.
- Sonar dashboard buckets must be mutually exclusive (`clean + quality_problem + pending` should not exceed the denominator), with quality problems classified before pending/error/missing states.
- Verify throughput/AI metrics are framed as context signals, not productivity ratings.
- Check config default/override ordering carefully: committed defaults must not override explicit CLI flags or environment selections.
- Validate Supabase and Sonar behavior separately: selected Supabase paths should require configured storage; non-Supabase paths should not. Missing Sonar config should skip or produce pending context without leaking tokens.
- Ensure scan windows include all rendered trend windows (for example trailing 12 weeks) and malformed cached timestamps surface as errors/pending context rather than silent undercounts.
- Workflow path filters should include the committed config/schema/testdata that drive the report; live schema mutation jobs should remain manually gated and least-privilege.

Minimum checks:

- Whether updates only open PRs or can be auto-merged.
- Cadence, open PR limits, grouping/noise, allow/ignore rules, and manifest directory coverage.
- Whether a minimum release age / cooldown exists to avoid immediately proposing newly published malicious or hijacked versions.
- Whether repo/org policy already uses an equivalent grace period elsewhere; if so, recommend mirroring it.

For Dependabot specifically, absence of `cooldown` is usually a strong hardening recommendation rather than an automatic blocker when PRs still require human review and CI. Escalate toward blocker/high-priority when the template is org-wide, automerge is enabled, or the user explicitly asks for min-release-age protection.

### 6) CI gates

By default, treat CI gates (`pre-commit-check`, `policy-bot:*`, metadata checks) as non-blocking process notes unless the user explicitly asks to enforce them as blockers.

Only enforce a gate as merge-blocking when the user requests that gate for decisioning.

### 6) Policy Bot / shared-template rollout safety

For PRs that change shared policy templates, CODEOWNERS, sync manifests, org-wide automation templates, or cleanup scripts that fan out PRs to many repositories:

- Validate the changed policy/config files directly when a validator exists (for Policy Bot templates, use the repo's documented validation endpoint or workflow; record validator version/output in the review note).
- Check that `policy.approval` rule names still resolve to defined `approval_rules` after renames/removals; YAML syntax alone is not enough.
- Preserve intentionally existing safety conditions such as signed commits, required statuses, branch/path scoping, `allow_author`, and `invalidate_on_push`; call out any removed condition explicitly.
- Inspect the sync manifest that distributes the template. A PR can make a template correct but still fail rollout if a repo appears in multiple groups that write the same destination (for example, two groups both syncing `.policy.yml`). Treat duplicate destination mappings as a rollout risk to verify, not automatically as a code blocker.
- For cleanup scripts that open downstream PRs across a manifest repo set, verify the cross-repo operational assumptions before approving: target labels used by `gh pr create --label ...` exist in all target repos (or the script handles missing labels), the cleanup branch does not already exist without an open PR when using `git push --force-with-lease`, and any signed-commit requirement such as `git commit -S` is documented or configured by the runner. Treat missing checks as a non-blocking caveat when the script opens reviewable PRs and live probing shows assumptions currently hold; escalate if the script directly mutates default branches or assumptions are false.
- For shared composite actions consumed by downstream workflows via `OWNER/REPO/path/to/action@main`, treat action input/output changes as a public API. If the PR removes or renames required inputs, search live downstream consumers before approving (for example `gh search code 'OWNER/REPO/path/to/action@main old_input org:ORG'`). A template update that syncs after merge is not atomic protection: consumers can resolve the new `@main` action before their workflow PRs/secrets land. Require a backward-compatible transition, versioned/new action path/ref, or verified two-phase rollout before merging.
- Distinguish enforcement from notification: a Policy Bot `requires.teams` rule can enforce team approval even if `options.request_review` is absent. Missing `request_review` is usually a usability/notification issue unless repo policy requires auto-requesting reviewers.
- For team-based approval changes, verify or explicitly flag the operational dependency that the intended actors are members of the required GitHub team before rollout.

### 6) Terraform / infra plan safety

For Terraform or infrastructure PRs:

- Review plan/apply output, not just source diff.
- For GCP GitHub Actions WIF bootstrap/scaffold PRs, use `references/gcp-github-actions-wif-bootstrap-prs.md`: require current Digger plan evidence, human/policy approval for material IAM changes, and explicit lifecycle/management for privileged bootstrap grants before approving. For large cross-cloud `infrastructure-iam` scaffolds that combine GCP WIF, Digger workflow routing, AWS OIDC roles, Terraform state buckets, bootstrap scripts, and multi-root plans, also use `references/infrastructure-iam-wif-scaffold-case.md` for the approval-level evidence pattern and common AWS/GCP provider pitfalls.
- For Terraform/Grafana alert contact-point or notification-route PRs that add webhook URL fallbacks, use `references/terraform-alert-webhook-fallbacks.md`: preserve existing normalized fallback chains (for example flat URL variable plus nested object `.url`), verify Digger/current plans, and treat dropped supported webhook paths as request-changes-level until fixed.
- For BigQuery-backed Grafana SLO PRs, use `references/bigquery-backed-grafana-slo-prs.md`: verify numerator/denominator population alignment, terminal-state semantics for Firestore/CDC rows, SQL-vs-SLO-window semantics, environment/datasource assumptions, and current Digger plan evidence.
For Grafana dashboard Terraform PRs whose code diff is scoped but the production Digger plan includes unrelated shared datasource drift, use `references/grafana-dashboard-digger-drift-case.md`: an explanation that the drift came from an earlier unapplied PR is provenance, not apply-safety; require a clean/reconciled plan, split apply, or explicit production-owner sign-off before approval.
- If the plan includes unrelated destroy/replace/removal not clearly explained by the authored change, treat it as a blocker by default.
- Do not approve solely because the file diff looks safe if the plan shows unexplained destructive changes elsewhere.
- Require one of:
  1. unrelated destroy is removed,
  2. author clearly explains why it is expected and in-scope,
  3. PR is narrowed/split so destructive change is explicitly reviewed.
- For user/group/import-style Terraform PRs, prefer the conservative rule: zero unrelated destroys before approval.
- For docs-only Terraform PRs or agent-guidance PRs, still inspect Digger/Terraform output. If the plan shows unrelated in-place drift with no add/destroy/replace, do not make that drift a request-changes blocker by itself; approve the docs if safe, but call out an operational caveat not to run `digger apply` from the docs-only PR unless the owner confirms the drift is intended. See `references/terraform-docs-pr-digger-drift.md`.

For tiny docs/comment/no-op Terraform-adjacent PRs whose explicit purpose is to give Digger an apply context for previously merged but unapplied infrastructure, use `references/terraform-bootstrap-apply-trigger-prs.md`: treat them as rollout/apply-safety reviews, verify the latest Digger plan now shows the intended bootstrap resources, check for zero destroys/replacements and no premature traffic cutover, then separate code/Terraform approval from remaining process gates or stale review states.

For recreated/superseded Terraform PRs whose current Digger plan is locked or blocked but an older PR had the same PR-owned diff and usable plan evidence, use `references/superseded-identical-terraform-pr-plan-evidence.md`: prove the old and current `base...HEAD` patch text is byte-identical, inspect the old Digger plan comments/checks directly, and if safe approve only the current code/content while requiring a fresh current-PR plan/apply as a process gate before merge.

For Google Workspace/user-onboarding Terraform PRs, see `references/google-workspace-onboarding-prs.md`. In short: verify the linked onboarding ticket against the user data, preserve repo ordering for users/groups/constants, inspect the latest Digger plan, allow clearly documented non-destructive in-place drift as a process caveat, and separate restricted-word/policy-bot/apply gates from code/data blockers. For re-reviews where earlier alias/settings blockers may be stale and Digger could not post the full plan because the comment exceeded GitHub limits, also use `references/google-workspace-import-digger-plan-recheck.md`: pull the linked Digger run logs, distinguish true removals from Terraform list reordering (`- value` plus `+ value`), classify outdated unresolved inline threads against current code/plan, and only post after a final head/current-decision check. For import-preserve PRs where the plan adds blanket generated group descriptions such as `+ description = "Imported existing Google Workspace group for ..."`, use `references/google-workspace-import-description-drift.md`: treat those as real metadata writes (not ordering noise) and request changes unless the cleanup is explicitly scoped/justified or the plan is updated to preserve blank live descriptions.

For team-membership or access-data PRs where a one-line YAML/JSON membership change fans out to IAM/AWS/Google Workspace access, see `references/team-membership-iam-access-prs.md`: parse the data, check ordering/duplicates, trace inherited privileges, require broad-access disclosure or acceptance, inspect current plan output, and classify stale old-head/process blockers separately from current code/data risk.

For IAM/team-membership access PRs that add a user to YAML team data and thereby grant cloud access through existing group/policy wiring, use `references/iam-team-membership-access-prs.md`: validate YAML ordering/duplicates and repo-wide membership occurrence, trace inherited AWS/GCP permissions for the target team/accounts, compare the live Linear ticket with any stale GitHub linkback text, classify explicit inherited-admin disclosure as a possible resolution of earlier scope blockers, and separate code/data approval from policy-bot/Digger apply gates.

For GitHub repository/ruleset Terraform changes that fan out across many repos, also check archived repositories before approving. See `references/terraform-archived-repo-ruleset-rollout.md`: a plan with only in-place ruleset changes can still be request-changes-level if Digger apply fails after partial modifications because GitHub rejects archived-repo ruleset updates as read-only. On re-review, validate both the already-failed archived repos and future archive transitions; a robust fix keeps ruleset inputs stable across archival so Terraform does not plan post-archive mutations. Require a fresh successful Digger plan, and separate code approval from remaining Digger apply/process gates.

For Terraform PRs that compose or manage runtime secrets (AWS Secrets Manager, SSM parameters, external-secrets payloads):

- Verify the generated secret keys match the application config contract, not only that Terraform validates. Search the app config/env examples/tests for expected names such as `MYSQL_*`, `REDIS_URL`, `BULLMQ_QUEUE_NAME`, etc.
- Confirm remote-state output names used by the new stack actually exist in the upstream roots/modules, especially sensitive outputs and optional outputs guarded by `try(...)`.
- Treat secret-bearing Terraform state as an explicit operational risk: approving is fine when intentional and documented, but call out missing documentation if a PR writes plaintext/composed secrets into Terraform-managed resources.
- Inspect the Digger/Terraform plan for the exact resource count and actions. A create-only plan for new secrets is usually safe; any unexpected replacement/destroy of secret versions or secrets needs explanation.
- Watch for rotation/drift semantics: if Terraform snapshots a vendor-managed or RDS-managed secret value into another runtime secret, future password rotation may require a re-apply or automation to keep the composed secret fresh. Usually note as non-blocking unless rotation is already active and no refresh path exists.
- For reusable secret modules with a flag like `ignore_secret_string_changes`, check whether toggling the flag swaps mutually exclusive `aws_secretsmanager_secret_version` resources and creates a new version. This is often non-blocking but worth documenting for future callers.
- For generated connection URLs, distinguish `null` optional credentials from empty strings. If upstream can emit `""`, require/coax a `length(...) > 0` guard to avoid malformed URLs such as `rediss://:@host`.

### 7) AI-agent workflow push safety

See also `references/ai-agent-workflow-push-safety.md` for a compact checklist and blocker examples from a real review.

For PRs that add AI-assistance label/disclosure gates or org-wide synced PR-template enforcement, also use `references/ai-label-check-workflow-review.md` for `pull_request_target` trust-boundary, skip-before-side-effects, race-safe label seeding, deterministic section validation, and sync-rollout checks.

When a PR changes CI/workflows that allow AI agents, bots, or review assistants to edit, commit, push code, or make pass/fail decisions from PR diffs:

- Treat the workflow wrapper as a security boundary only if the AI process cannot access push-capable credentials directly.
- Check `actions/checkout` for `persist-credentials: false` when a write token is used before an agent/LLM step. Default persisted checkout credentials in `.git/config` can let the agent push before wrapper verification. For prompt-only/read-only AI audits, still prefer `persist-credentials: false` when git credentials are unnecessary.
- Check the agent execution step environment for `GH_TOKEN`, PATs, app tokens, provider auth files (`CODEX_AUTH_JSON`, `~/.codex/auth.json`, etc.), or remote credentials with contents-write/read scope. If the model has unrestricted shell/bypass-sandbox access and credential material is readable, wrapper-side isolation is not enforceable.
- For reusable AI-review workflows, do not let a new scoped GitHub App/check-run wrapper distract from a legacy PAT still exported to the model process (for example `FINN_DEVOPS_PERSONAL_ACCESS_TOKEN` flowing through `REVIEW_GH_TOKEN` to `GH_TOKEN`). GitHub Actions `permissions:` do not constrain PAT scope; this remains blocker-level while the agent has shell/sandbox bypass.
- Treat PR body/diff text as untrusted prompt input. If a workflow appends `gh pr diff` into an agent prompt, do not approve `codex exec --dangerously-bypass-approvals-and-sandbox` or equivalent unrestricted tool execution unless an external sandbox/no-shell/no-network boundary is actually enforced.
- Require proactive branch gating for the policy in the ticket: same-repo, non-fork, non-base/default, and protected/ruleset branches when the acceptance criteria mention protected-branch rejection. Do not rely only on GitHub's eventual server-side push rejection if the workflow claims to reject safely before running fix mode.
- If commits should be attributed to a specific bot/account, verify the wrapper checks all commits created in the agent range (for example `BASELINE..HEAD`) for expected author and committer metadata before pushing. Setting `git config user.name` before the agent runs is not enough because the agent can change it.
- For AI-generated machine-readable decisions, verify parser fail-closed behavior: required fields, exact enum values and types, and only explicit pass states should pass CI. Unknown/uppercase/invalid statuses must fail.
- For prompt+diff CLI invocations, prefer stdin/file input over passing the entire diff as one command argument to avoid OS `ARG_MAX` failures.
- Prefer behavior tests that execute resolver/gating/token-safety/parser logic with fixtures over substring assertions against YAML.

### 7) Vendor Attributes API / identity attachment rollout safety

See also `references/vendor-attributes-api-rollout-safety.md` for a reusable checklist and blocker wording from a Shield Attributes API review.

For frontend follow-up PRs that reduce Shield SDK over-firing by removing eager initialization or deduplicating polling-driven screen sends, see `references/frontend-shield-dedupe-pr-case.md`. Key approve-level signals: feature-flag/sampling checks still happen before SDK/network work, dedupe is scoped per real checkpoint/state rather than suppressing the whole journey, module-scoped services reset dedupe on a new attempt, and stale backend Attributes API review threads are explicitly classified as resolved/outdated before approval.

When a PR moves client-side identity/attribute attachment to a backend vendor Attributes API (fraud, risk, analytics, attribution, device-intelligence, etc.):

- Verify the PR moves only the intended identity fields server-side. Do not assume all client SDK calls are obsolete; native/web calls may also carry non-PII checkpoint, screen, lifecycle, device, or event context used by vendor rules/analytics.
- If prior review or vendor guidance says only `user_id`/identity moves backend, treat removal of non-identity SDK checkpoint calls as a blocker unless the author provides vendor-confirmed equivalence.
- Check for partial-success semantics: local bind/backfill state should not commit and then return `500` solely because a post-commit external vendor call failed unless there is durable retry/idempotency state.
- Prefer explicit attributes status (`pending`/`sent`/`failed`), `attributesSentAt`, retry/outbox, or another reconciliation path so vendor identity attachment eventually succeeds and retries are unambiguous.
- For existing inline threads covering the same missing SDK checkpoint/signal, avoid duplicate inline comments; mention that the existing thread remains blocking in the formal review body and post new inline comments only for distinct blockers.

### 8) Copy-only i18n / user-facing wording PRs

For PRs that only rename translated/user-facing copy in locale/resource files while intentionally preserving runtime identifiers, use `references/copy-only-i18n-prs.md`.

For country-scoped SMS/OTP/transactional-message copy changes, also use `references/country-scoped-sms-copy-prs.md`: verify the runtime message builder cannot still select old/branded copy through a mutable `user.language` when the requirement is scoped by country, provider, SenderID, or template type. For the concrete PH OTP case where a stale blocker was resolved by returning OTP-only before translation lookup, plus the scheduled-run force-push/base-refresh posting pitfall, see `references/finn-web-app-5025-country-otp-copy-case.md`.

Key checks:

- Verify the changed keys are the keys rendered by the affected screens/components, including summary/readback/disclosure surfaces.
- Confirm form controls, payload/API fields, analytics identifiers, enums, and i18n key names remain unchanged when the ticket requires a copy-only contract.
- For country-scoped copy, search all locale translations for the changed key and test target-country users with non-default languages if language can diverge from country.
- Search for old wording repo-wide but classify remaining matches carefully: current visible UI copy may block; internal logs/errors, comments, or intentionally preserved identifiers usually do not.
- Run resource syntax validation such as `jq empty` for JSON locales plus `git diff --check`; rely on current remote app/test CI for broad validation when the local devcontainer is blocked by private tooling.

### 8) Logging-only / observability-noise PRs

When a PR primarily changes logging levels, health-check logging, metrics noise, or other observability signal/noise behavior:

- Map the diff back to the ticket acceptance criteria one log source at a time. For example: health success-path logging removed, expected client/domain errors downgraded, unexpected/internal errors still elevated.
- Verify runtime behavior is unchanged unless explicitly intended: HTTP status codes, response bodies, error matching order, nil-logger safety, and error wrapping semantics should remain equivalent.
- Check both the directly changed handler and any global middleware/request logger; a health-handler log removal may not eliminate health spam if global request logging still logs the path.
- Treat PII/secrets in newly added or retained log fields as a blocker. Downgrading a log level does not make sensitive data safe to log.
- Prefer zap observer/log-capture tests for log-level acceptance criteria, but do not automatically block a small logging-only PR solely because existing tests assert only response behavior when local/remote suites pass and the diff is straightforward. Mention missing log-level regression tests as a non-blocking follow-up when appropriate.

### 8a) Internal telemetry ingestion / developer-usage dashboard PRs

For PRs that add or change internal developer/tool telemetry, local hooks, Supabase/Postgres ingestion, Edge Functions, or Grafana dashboards, use [`references/internal-telemetry-ingestion-prs.md`](references/internal-telemetry-ingestion-prs.md). Key checks: payload minimization (no prompt/command text/secrets/raw hostnames), token removal before subprocesses, bounded server validation, RLS/read-only dashboard roles, safe Grafana variable formatting such as `${team:sqlstring}`, dashboard time filters that match the selected range, and regression tests that parse dashboard SQL/JSON.

### 8b) Firebase Functions Express app-factory extraction PRs

For PRs that move Express app construction out of a Firebase Functions entrypoint into `createApp()` or another reusable factory for integration testing, use [`references/firebase-functions-express-app-factory-prs.md`](references/firebase-functions-express-app-factory-prs.md). Key checks: middleware/runtime parity, no Firebase trigger imports from the app factory, raw-body/webhook route scoping, Cloudflare/proxy gate behavior, non-production debug/docs gating, PII-safe logging/sanitization order, and preview/deploy workflow coupling such as API-prefix rename targets.

For Codex/agent telemetry tools specifically, also use [`references/codex-telemetry-ingestion-tools-case.md`](references/codex-telemetry-ingestion-tools-case.md). It captures the report-only parent-delegated review shape, safe validation commands, and a provenance pitfall: verify current-head approvals via review `commit_id` + PR `headRefOid`, not SHAs quoted inside older review bodies.

### 9) Docs-only implementation-plan/spec-contract PRs

For docs-only PRs where markdown files are intended to be executable implementation plans, migration contracts, sign-off checklists, or porting specs, use `references/docs-spec-implementation-plan-prs.md`. Treat these as contract reviews rather than prose reviews: verify dependency graphs, runnable test predicates, fixture/offline validation behavior, runtime/cutover claims, shell/env consistency, and checklist enforceability. A docs-only PR can be request-changes-level when an implementer following the spec would produce an unrunnable test, live-system fixture command, or invalid cutover order.

### 10) Docs-only agent guidance / centrally synced AGENTS.md PRs

For PRs that change centrally managed agent docs (`AGENTS.md`, `CLAUDE.md`, `other-templates/AGENTS.md`, `other-templates/README.md`, `.github/sync-other-files.yml`, or `other-templates/agent-docs/*`), use `references/docs-only-agent-guidance-prs.md`.

Key checks:

- Treat these as downstream documentation-contract rollouts, not trivial markdown edits.
- Verify mirrored root docs remain mirrored (`AGENTS.md`, `CLAUDE.md`, and the central template are usually byte-identical).
- Check read order and ownership wording for `AGENTS.repo.md`, `AGENTS.terraform.md`, and `AGENTS.<profile>.md`.
- Verify profile names against the sync manifest rather than assuming they equal source languages; for example Node.js / TypeScript may map to `AGENTS.nodejs.md`.
- Revalidate prior review threads on current head and mark stale findings resolved when current docs and manifest now agree.

### 11) Static HTML org chart / roster-sync PRs

For PRs that update a static employee org chart, roster, embedded data arrays, or department filter buttons in a static landing page, use `references/static-html-org-chart-prs.md`. Treat the changed HTML/JS as data plus UI contract: validate unique IDs/emails, parent references, one root, exact filter-to-department matches, rendered people counts, and browser filter behavior. Separate approve-level code/data consistency from stale Policy Bot or old AI-review `CHANGES_REQUESTED` process blockers.

### 12) Kubernetes / image-artifact rollout safety

For Kubernetes, Helm, or deployment-manifest PRs that wire hooks/scripts/binaries/config paths supplied by an application image, see also `references/kubernetes-prestop-image-artifact-rollout.md` for the concrete preStop hook/script checklist and approval wording.

For Kubernetes RBAC PRs that add read-only incident/debugging permissions (pod logs, events, endpoint metadata, ExternalSecret metadata, nodes, etc.), also use `references/kubernetes-read-only-diagnostics-rbac.md`: verify environment scope, least-privilege explicit resources/verbs, no mutating or interactive verbs, role separation from baseline `read-only`, and log/secret exposure caveats.

- Verify the currently referenced image tag/artifact actually contains the file or behavior being wired. Do not assume merged application PRs are sufficient if the deployment manifest still points to an older tag.
- For GitHub-hosted app repos with semver tags, a quick check is:
  ```bash
  gh api "repos/OWNER/APP_REPO/contents/path/to/file?ref=vX.Y.Z" --jq '.sha + " " + (.size|tostring)'
  ```
  Treat a 404 at the deployed tag but success at the newer tag/main as a rollout blocker unless the PR explicitly sequences an image bump separately.
- If a preStop/lifecycle hook falls back when a script is absent, ensure it does not also hide non-zero exits from the script. Prefer an explicit branch such as:
  ```bash
  if test -x shell/kafka-graceful-shutdown.sh; then shell/kafka-graceful-shutdown.sh; else sleep 15; fi
  ```
  over `test -x script && script || fallback`, because the latter also runs the fallback after script failure.
- Compare staging/prod counterparts for drift in helper usage, labels, selectors, resource defaults, node selectors, and image tags; staging validation only proves production safety if the production manifest points at equivalent artifacts and logic.
- For Argo CD hook/migration PRs, check both hook execution semantics and app-image artifact compatibility. If an Application has `ApplyOutOfSyncOnly=true`, a `PreSync` hook may not reliably gate the rollout; also verify the exact image tag used by both the Deployment and hook Job contains every required migration script and post-migration runtime provider/feature. See `references/argocd-presync-selective-sync-image-artifacts.md`.

## PR Review Memory

Persist review continuity outside the chat so follow-ups can resume without re-reading everything.

Preferred locations:

- Project-local: `.hermes/pr-reviews/<repo>-<pr-number>.md`
- If no project directory is available: `${HERMES_HOME:-~/.hermes}/pr-reviews/<repo>-<pr-number>.md`
- For disposable PR review worktrees/checkouts where you will run `git status` as a cleanliness signal, prefer the Hermes-home location (or an ignored project-local review path) so review notes do not leave untracked `.hermes/` files in the candidate checkout. If project-local memory is useful, explicitly distinguish the review-note artifact from PR-authored changes in the final verification.

Append dated sections on re-review; do not overwrite history. Keep a live status board at the top.

Before writing or replacing a review-memory file, read the existing file when it exists, especially in scheduled/batch runs or when tool output warns that a sibling subagent modified it. Patch/append instead of blind overwrite so concurrent reviewer lanes or earlier verification notes are not lost.

Minimum sections:

1. PR metadata: repo, URL, branch/base, latest head SHA
2. Current status board: OPEN / RESOLVED / DONE / WONTFIX per issue
3. Current verdict
4. Blockers / high-priority / suggestions
5. CI/policy snapshot
6. Merge readiness + next actions
7. Internal token usage, if available (Reviewer A, Reviewer B, parent/synthesis, total; never for GitHub posting)
8. Posted-comment links, if any

When the user later asks about the same PR, read the existing review note first, then diff-check what changed.

## User-Facing Chat Output

Default chat response for a PR review or re-review:

```text
<repo> #<pr-number> — <title>
🔗 <full PR URL>
Verdict: <Approve | Needs changes | Blocked | Pass>
Models: Reviewer A: <openai-codex/gpt-5.5 or actual>, Reviewer B: <direct Claude CLI / actual / unavailable>
Token usage: Reviewer A: <tokens|unavailable>, Reviewer B: <tokens|unavailable>, parent/synthesis: <tokens|unavailable>, total: <tokens|unavailable> (internal only; not posted to GitHub)
Why:
- <2-5 concrete bullets>
Merge readiness: <merge-ready | not merge-ready | merge-ready after X>
GitHub action: <approved | requested changes | commented | not posted yet>
```

For re-reviews, also include:

- `What changed since last review:` with resolved vs still-open items.
- `Author/thread context:` when prior blockers had author replies, including the reply classification (`clear + credible`, `clear but unimplemented`, `unclear/needs clarification`, or `disagreement needing evidence check`) and how it changed the decision.
- Explicitly call out stale prior findings.
- If author context is unclear, ask the smallest targeted clarification question needed before repeating/requesting changes.

Do not reduce the output to only `Decision` / `Because` unless the user explicitly asks for an ultra-short format.

## PR Communication Rules

### Parent-delegated / subagent review mode

When the requester is a parent agent (or explicitly says things like `DO NOT post comments/reviews to GitHub`, `DO NOT send chat messages`, `return a structured result for the parent to post`, or `after final head verification`):

- Treat the task as **report-only to the parent**. Do not post GitHub comments/reviews, do not send separate platform messages, do not rename/archive Discord/Telegram threads, and do not create noisy progress updates.
- Still run the full guardrail workflow: live PR freshness, local checkout/diff review, relevant tests/checks, direct Claude CLI lane when practical, synthesis, and a final head recheck.
- Return a concise structured result plus a complete proposed formal GitHub review body/action that the parent can post after its own final head verification.
- In structured output, separate actual external side effects from recommendations. Prefer fields like `github_action_performed: "none (parent-delegated)"` and `github_action_proposed: "APPROVE"`; do not put `APPROVE` under an unqualified `github_action` field when nothing was posted.
- Clearly label any process gates separately from code blockers, and include the exact current head SHA reviewed.
- Do not say `GitHub action: approved/requested changes` unless a GitHub action was actually authorized and performed; use `GitHub action: not posted (parent-delegated)` or similar.

- Always finish with a chat summary unless the requester explicitly asked for parent-delegated/no-chat-message mode; in that mode, return only the requested structured result to the parent.
- Default for this user/workflow: **post the review to GitHub** unless the user explicitly says `chat-only`, `do not post`, `don't comment`, `DO NOT post comments/reviews`, or equivalent.
- When posting by default, choose the formal GitHub review action from the synthesized verdict:
  - `APPROVE` for approve / merge-ready verdicts.
  - `REQUEST_CHANGES` for blockers, needs-changes, or request-changes-level issues.
  - `COMMENT` only when the result is intentionally informational/uncertain and should not approve or block.
- Include a complete review body that satisfies the APPROVE / REQUEST_CHANGES requirements below; do not post one-line formal reviews.
- Post inline comments only for concrete actionable code-level blockers/high-priority issues where line placement is useful and not duplicative. Otherwise, use the formal review body for the summary.
- If a formal approval is rejected because the active GitHub token belongs to the PR author (`Review Can not approve your own pull request`), do not treat the code review as failed. Post the approve-level review body as a top-level PR comment, verify the comment, report `GitHub action: commented (formal approval unavailable: own PR token)`, and use the Discord/thread status `Commented` rather than `Approved`.
- Respect explicit opt-outs exactly: if the user says chat-only / do not post / don't comment, skip GitHub comments/reviews and deliver chat only.
- Respect conditional GitHub-posting instructions exactly. If the user says, for example, "post inline comments and a summary review if there are blockers; otherwise keep summary in this thread," then:
  - Post to GitHub only when synthesized findings include blockers / request-changes-level issues.
  - If no blockers are found, do **not** post an approval, summary comment, or inline nits; deliver the full result in chat only.
  - Mention in the final chat summary that GitHub was not posted because the condition was not met.

### GitHub comment formatting

For GitHub summary/review comment headings, use the generic title format:

```text
Guardrail review — <RESULT>
```

Examples: `Guardrail review — Approved`, `Guardrail review — Needs changes`, `Guardrail review — Blocked`.

Do not prefix the heading with `Hermes` or `Hermes guardrail review` unless the user explicitly asks for product-branded comments.

1. Never send multi-line comment bodies with escaped `\n` strings.
2. Use `gh pr comment --body-file - <<'EOF' ... EOF` for summary comments when the shell/tooling permits heredocs.
   - If the terminal/tool wrapper rejects a foreground command because markdown text inside the heredoc contains shell-looking control characters such as `&` (for example a heading like `Quality & signals`), write the body with the file/write tool first and then run `gh pr review/comment --body-file /tmp/body.md`. Do not keep retrying or rewrite the review body to appease the shell parser.
3. For inline comments, prefer `gh api ... -F body@/tmp/comment.md` with a temp markdown file.
4. If using `gh api ... -f body="..."`, keep it single-line only.
5. Use fenced code blocks for snippets.
- Re-read posted comments quickly; patch formatting if broken.
- After posting a formal review, verify it with the pulls reviews API, not only `gh pr view --json latestReviews`; `latestReviews` can omit the newly submitted viewer review or continue showing older review-decision state while policy/human gates remain unresolved. Use:
  ```bash
  gh api repos/OWNER/REPO/pulls/PR_NUMBER/reviews --paginate \
    --jq '[.[] | {id,user:.user.login,state,submitted_at,commit_id,body:(.body[0:80])}] | .[-8:]'
  ```
  If shell/JQ argument passing gets brittle (for example `gh api --jq --arg ...` fails with `accepts 1 arg(s), received 4`), do not keep retrying malformed `gh` invocations. Save the reviews JSON to a temp file and filter it with Python using the live `headRefOid`; this is a reliable pattern for detecting existing current-head `poom` decisions and verifying the newly posted review id/commit. For provenance/delta checks, trust the review object's `commit_id` and PR `headRefOid` over SHAs quoted in the review body text. Review bodies can mention an intermediate or previously reviewed SHA even when the formal review record is attached to the current head; diffing that quoted SHA to HEAD can create huge unrelated false deltas.
- When recovering from a prior failed review run where local memory/chat says the PR was reviewed but GitHub has no current-head formal review, re-check the live PR head SHA and formal reviews first. If the head matches the saved review memory and no matching submitted `APPROVE`/`REQUEST_CHANGES` exists for the current head, submit the missing decision using the normal full review-body format reconstructed from `.hermes/pr-reviews/<repo>-<number>.md` or `${HERMES_HOME:-~/.hermes}/pr-reviews/<repo>-<number>.md`: verdict, why, findings/evidence, merge readiness, and next actions. Never post a thin administrative “submitting missing decision” note as the review body; if the saved memory is too thin, re-run or narrowly re-validate the review to produce a complete body.
- If the user explicitly asks to **supersede** Poom's own prior current-head `REQUEST_CHANGES` after new evidence (for example Digger/Terraform plans) becomes available, do not apply the normal duplicate-current-head-decision skip. Re-review the current head and old blocker, verify the new evidence resolves the blocker, sample the head immediately before posting, then submit a full formal `APPROVE` review on the same head to supersede the earlier Poom changes-requested review. Verify the new approval through the pulls reviews API. If another reviewer still has `CHANGES_REQUESTED`, `reviewDecision` may remain `CHANGES_REQUESTED`; report that separately as process/human-gate state, not as failure to supersede Poom's review.
7. Keep one idea per inline comment.
8. Before posting inline comments, query existing PR review comments (`gh api repos/OWNER/REPO/pulls/PR/comments --paginate`) and de-duplicate by path/line plus issue substance. If an equivalent unresolved blocker is already present, do not post a duplicate inline comment; instead mention in the summary review that the existing thread remains blocking, or post only newly discovered blockers.
9. When generating markdown files from shell scripts, use quoted heredocs (`cat <<'EOF'`) or `write_file`; unquoted heredocs will execute backticked code spans and `$(...)`, corrupting review notes and possibly running unintended commands.

## GitHub Review Body Requirements

### APPROVE body

Must include:

1. What was checked/rechecked
2. Why it is safe to merge
3. Any important non-blocking follow-up

### REQUEST_CHANGES body

Must include:

1. Blockers/high-priority issues
2. Why they matter
3. Concrete fix direction

Do not post one-line approve/request-changes bodies unless explicitly requested.

## Reference Index

Durable supporting references for specialized review paths:

- [Angular / Node major-version migration PR reviews](references/angular-node-major-migration-prs.md)
- [Atlas Scout Reports package skeleton / executable-spec PR case](references/atlas-scout-reports-package-skeleton-case.md)
- [Atlas Scout Reports runtime consolidation PR case](references/atlas-scout-reports-runtime-consolidation-case.md)
- [Atlas Scout TA Refresh Source Tracking strict `job_id` PR case](references/atlas-scout-ta-refresh-source-tracking-job-id-case.md)
- [Atlas Scout Reports source-migration PR case](references/atlas-scout-reports-source-migration-case.md)
- [Copy-only i18n / user-facing wording PR reviews](references/copy-only-i18n-prs.md)
- [Certification-only tests/CI PRs with stale production-change history](references/certification-only-test-ci-prs.md)
- [BigQuery-backed Grafana SLO PR reviews](references/bigquery-backed-grafana-slo-prs.md)
- [Grafana dashboard Terraform PRs with unrelated Digger datasource drift](references/grafana-dashboard-digger-drift-case.md)
- [Codex telemetry ingestion tool PR case](references/codex-telemetry-ingestion-tools-case.md)
- [Terraform Grafana SLO PRs with missing Digger plan and later current-head re-review](references/terraform-slo-pr-missing-plan.md)
- [AI agent workflow push safety](references/ai-agent-workflow-push-safety.md)
- [AI-review workflow PR-branch dispatch](references/ai-review-workflow-pr-branch-dispatch.md)
- [Base-refresh during review + stale process-gate rows](references/base-refresh-and-process-gate-pr-case.md)
- [Current-head approval after a small post-approval delta](references/current-head-approval-after-small-delta.md)
- [Dependency automation hardening](references/dependency-automation-hardening.md)
- [Dependabot PolicyBot bypass safety](references/dependabot-policybot-bypass-safety.md)
- [Frontend Shield SDK over-firing / per-state dedupe PR case](references/frontend-shield-dedupe-pr-case.md)
- [GitHub review verification quirks](references/github-review-verification-quirks.md)
- [GitHub PR review SLA alert workflow reviews](references/github-pr-review-sla-alert-tools-case.md)
- [IAM/team membership access PR reviews](references/iam-team-membership-access-prs.md)
- [Google Workspace import Digger plan recheck](references/google-workspace-import-digger-plan-recheck.md)
- [Google Workspace import generated description drift](references/google-workspace-import-description-drift.md)
- [GitHub Actions release-marker workflow reviews](references/github-actions-release-marker-workflows.md)
- [GitHub Actions workflow_dispatch tag-validation reviews](references/github-actions-workflow-dispatch-tag-validation.md)
- [GitHub Actions issue_comment smoke tests with secrets](references/github-actions-issue-comment-secret-smoke-tests.md)
- [Internal telemetry ingestion / developer-usage dashboard PRs](references/internal-telemetry-ingestion-prs.md)
- [Docs-only agent guidance / centrally synced AGENTS.md PRs](references/docs-only-agent-guidance-prs.md)
- [Docs-only IAM grant delta after prior approval](references/docs-only-iam-grant-delta-after-approval.md)
- [Docs/spec implementation-plan PR reviews](references/docs-spec-implementation-plan-prs.md)
- [SonarCloud / coverage workflow PR reviews](references/sonarcloud-coverage-workflow-prs.md)
- [Superseding Poom's own current-head REQUEST_CHANGES after new evidence](references/supersede-current-head-request-changes.md)
- [Superseded identical Terraform PR plan evidence](references/superseded-identical-terraform-pr-plan-evidence.md)
- [Go CLI review quirks](references/go-cli-review-quirks.md)
- [GCP GitHub Actions WIF bootstrap PRs](references/gcp-github-actions-wif-bootstrap-prs.md)
- [Kubernetes preStop hook + image artifact rollout reviews](references/kubernetes-prestop-image-artifact-rollout.md)
- [Kubernetes read-only diagnostics RBAC reviews](references/kubernetes-read-only-diagnostics-rbac.md)
- [Static HTML org chart / roster-sync PRs](references/static-html-org-chart-prs.md)
- [Learn preload / impression attribution PR case](references/learn-preload-impression-attribution-pr-case.md)
- [Paginated API producer/consumer contracts](references/paginated-api-consumer-contracts.md)
- [Paginated membership-period sync case study](references/paginated-membership-period-sync-case.md)
- [Process gate and check-status quirks](references/process-gate-check-quirks.md)
- [Failed finn-ai-coder review check classification](references/finn-ai-coder-failed-check-classification.md)
- [PR velocity / aggregate Chat report config reviews](references/pr-velocity-chat-config-review.md)
- [PR velocity dashboard views / local Supabase dashboard reviews](references/pr-velocity-dashboard-views-case.md)
- [PR velocity Sonar + roster filter fix case](references/pr-velocity-sonar-roster-filter-fix-case.md)
- [PR velocity Chat config parent-delegated case: EWA-Services/Tools #133](references/pr-velocity-chat-config-tools-133-case.md)
- [Python/Poetry unavailable test fallback](references/python-poetry-unavailable-test-fallback.md)
- [Rebase / force-push during review](references/rebase-force-push-during-review.md)
- [Runtime config defaults rollout safety](references/runtime-config-defaults-rollout-safety.md)
- [Terraform archived-repository ruleset rollout failures](references/terraform-archived-repo-ruleset-rollout.md)
- [Terraform docs-only PRs with Digger drift](references/terraform-docs-pr-digger-drift.md)
- [Head changed after drafting a review body](references/head-changed-after-drafting-review.md)
- [Head changes after drafted request-changes near tool-budget cutoff](references/head-changed-request-changes-cutoff.md)
- [AI label check workflow reviews](references/ai-label-check-workflow-review.md)
- [Atlas Scout Reports Python floor / timeout follow-up](references/atlas-scout-reports-python-floor-timeout-followup.md)
- [Country-scoped SMS copy PRs](references/country-scoped-sms-copy-prs.md)
- [Finn AI coder refresh check noise](references/finn-ai-coder-refresh-check-noise.md)
- [Force-rule feature-flag integration PR case](references/force-rule-feature-flag-integration-pr-case.md)
- [GitHub Actions required-checks comment workflows](references/github-actions-required-checks-comment-workflows.md)
- [Google Workspace onboarding PRs](references/google-workspace-onboarding-prs.md)
- [Python src-layout package PRs](references/python-src-layout-package-prs.md)
- [Review body template](references/review-template.md)
- [Stacked stale PR diff noise](references/stacked-stale-pr-diff-noise.md)
- [Team-membership IAM access PRs](references/team-membership-iam-access-prs.md)
- [Terraform alert webhook fallbacks](references/terraform-alert-webhook-fallbacks.md)
- [Terraform bootstrap apply-trigger PRs](references/terraform-bootstrap-apply-trigger-prs.md)
- [Vendor Attributes API rollout safety](references/vendor-attributes-api-rollout-safety.md)
- [Volatile PR heads](references/volatile-pr-heads.md)

## Verification Checklist

- [ ] Current head SHA checked
- [ ] Live diff and changed files checked
- [ ] Title/body/comments checked
- [ ] Inline review threads, author replies, and other reviewers' decisions checked
- [ ] Prior blocker/thread ledger created for re-reviews, with author replies classified and current-code evidence checked before repeating findings
- [ ] Linked ticket/experiment context checked or missing-ticket issue recorded
- [ ] CI/checks/review state checked
- [ ] Head SHA rechecked immediately before posting; volatile PRs double-sampled or revalidated after force-push
- [ ] For shared policy/template PRs: validator output, rule-reference integrity, sync-manifest destination conflicts, and team-membership/notification dependencies checked
- [ ] Reviewer A completed or explicitly unavailable
- [ ] Reviewer B direct Claude CLI completed or explicitly unavailable
- [ ] Findings synthesized with stricter verdict
- [ ] Internal token usage captured/reported when available and omitted from GitHub comments/reviews
- [ ] Review memory updated
- [ ] GitHub comments/review posted only if authorized
- [ ] Final chat summary delivered to origin Discord thread / Telegram topic / chat
