# Preserved Pending PR Review Guide

This reference preserves the previous detailed operating guide. Use it for step-by-step procedures after the lean `SKILL.md` routes to this skill.

## Previous Frontmatter

```yaml
name: pending-pr-review
description: Use when Poom asks to review pending PRs, check the review queue, batch-review open GitHub PRs awaiting review, or recover missing submitted GitHub review decisions from saved review memory; lists pending PRs and runs pr-review-guardrails for each PR with one user-facing message/thread per PR.
version: 1.0.0
license: MIT
required-skills: [pr-review-guardrails]
required-binaries: [bash, gh, python3]
required-env: []
required-mcps: []
metadata: github-pr-review-queue
```

## Previous Operating Guide

# Pending PR Review

## Overview

Reference: `references/github-search-limit-before-filtering.md` documents the durable pitfall where `gh search prs --limit` truncates raw results before local draft/bot/automerge filtering, causing legitimate human review requests to disappear unless the raw limit is high enough.

Reference: `references/cron-start-vs-output-finalization.md` documents why an hourly Hermes cron round can have started even when `last_run_at` and the output file still show the previous run.

Use this skill to batch-process Poom's pending GitHub review queue. It is migrated from the OpenClaw `pending-pr-review` skill and adapted for Hermes.

Workflow:

1. Fetch pending PRs awaiting Poom's review.
2. For each PR, run the **`pr-review-guardrails`** workflow as the authoritative per-PR review policy.
3. Post GitHub review comments/decisions according to the user's instruction.
4. Report back to the user as **one message per PR**, so each PR can continue in its own Discord thread or Telegram topic when supported.
5. Include internal per-PR token usage in the user-facing chat/Discord result when available; do not post token usage to GitHub unless explicitly requested.

This skill is a batch orchestrator only. It must not replace or weaken the `pr-review-guardrails` checks for individual PRs.

## When to Use

Use when the user says things like:

- "review pending PRs"
- "check my review queue"
- "what PRs are waiting for me?"
- "batch review my PRs"
- "review all open PRs pending my review"

Do not use when the user gives a single PR URL; use `pr-review-guardrails` directly for one PR.

## Queue Discovery

### Operational cron status check

When Poom asks whether the pending-review cron is running, answer operationally rather than starting a review run:

1. Use Hermes cron listing/status (`hermes cron list` or cronjob list tool, plus `hermes cron status`) to locate the `pending-pr-review` job and verify the gateway scheduler is alive.
2. Report the job id/name, `enabled`, `state`, schedule, last run/status/error, next run, and delivery target.
3. Check if it is actively executing before saying “running now” (for example `ps aux | grep -E '<job-id>|pending-pr-review|hermes chat|cron' | grep -v grep`). Distinguish “enabled/scheduled” from “currently executing.” If the only match is an old `rmux`/`claude --tools ''` reviewer lane under `/tmp/pending-pr-review-rmux/...` with no live Hermes cron/chat process for the job, report it as a stale leftover reviewer subprocess, not as the cron job running. Do not trigger another run when the user asked “if running, no need to trigger” until this distinction is clear.
4. If the user asks what a stale `claude --tools ''` rmux child means, explain compactly: it is a prior reviewer lane launched by the workflow that likely got stuck/idle and did not exit cleanly; it is not the hourly Hermes cron job itself, though it may consume resources and confuse process-name checks. Do not kill it unless the user explicitly asks for cleanup.
5. If the user asks about the last run outcome, inspect the latest `<home>/.hermes/cron/output/<job-id>/*.md` and relevant gateway error log lines; summarize compactly and preserve the queue distinction between raw pending items and “no unreviewed PRs remain.”
5. If the user is waiting for a specific run result and the latest output ended with a cutoff/error, read the end of the output file first and recover any explicitly unfinished work according to `references/cron-cutoff-recovery-after-user-waits.md`: verify current head + current-head `poom` review state before posting any saved draft body, avoid duplicate GitHub reviews, complete missing deliver-local Discord messages, then re-list the live queue.

Default queue parameters, inherited from the OpenClaw workflow:

- GitHub owner/org: `ewa-services`
- Reviewer: `poom`
- State: open
- Exclude drafts
- Exclude bot/noisy automation authors from the raw GitHub search (`finn-devops`, `dependabot[bot]`, `dependabot`, `codegen-sh`) so they do not consume the GitHub search result limit before local filtering
- Exclude PRs labeled `automerge`

Preferred command, when running from this skill directory:

```bash
bash scripts/list_pending_prs.sh --json
```

For diagnostics and scheduled summaries, prefer:

```bash
bash scripts/list_pending_prs.sh --stats-json
```

`--stats-json` returns `{prs, filter_stats}` where `filter_stats.dropped_by_local_filter` is the number of raw search results discarded locally after GitHub search. If `filter_stats.risk_hidden_by_local_filter` is true, the raw result hit `--limit` and local filtering dropped items, so valid human PRs may be hidden beyond the limit; increase `--limit` or push the filter into the GitHub query.

The pending queue is a **review-request queue**, not Poom's authored/open-PR queue. When the user asks why the queue count is high or whether items are "just requesting me," explain that the script uses GitHub `--review-requested=<reviewer>`; list entries are PRs where GitHub still says Poom is requested as reviewer after the local filters. To distinguish truly unreviewed PRs from process/merge-blocked leftovers, inspect each listed PR with `gh pr view <num> --repo <owner/repo> --json reviewRequests,reviewDecision,mergeStateStatus,headRefOid` and `gh api repos/<owner/repo>/pulls/<num>/reviews --paginate`, then filter for `user.login == "poom"`, `commit_id == headRefOid`, and `state in (APPROVED, CHANGES_REQUESTED)`. Report counts separately, e.g. `7 still need Poom review; 1 already has a current-head Poom decision but remains listed due review-request/process/merge state`.

The script sends `--draft=false` plus negative author qualifiers to GitHub search itself (`-author:finn-devops`, `-author:dependabot[bot]`, `-author:dependabot`, `-author:codegen-sh`) before applying local draft/bot/automerge filtering. This prevents draft and automation PRs from consuming `--limit` slots and hiding human PRs.

If the current working directory is elsewhere, use the installed skill path:

```bash
bash ${HERMES_HOME:-$HOME/.hermes}/skills/github/pending-pr-review/scripts/list_pending_prs.sh --json
```

The script returns a JSON array with at least:

- `repository.name`
- `number`
- `title`
- `author.login`
- `url`
- `labels`
- `isDraft`

If the queue is empty, report exactly:

```text
No pending PRs — queue is clear ✅
```

## Batch Execution Policy

For each PR in the queue:

1. Treat the PR as an independent review task.
2. Use `pr-review-guardrails` as the per-PR review policy.
3. Use one dedicated worktree per PR when local checkout is needed:
   - Preferred: `<workspace>/repo/<repo-name>-<pr-number>`
   - Do not put PR worktrees directly in a workspace root.
4. Use repo-qualified labels to avoid collisions:
   - Required base pattern: `<repo-name>-pr-<pr-number>`
   - Never use plain labels like `pr<number>` or `pr<number>-reviewer-a`.
5. Parallelize only when practical and safe. Keep enough separation that results and worktrees cannot collide.
   - Hermes `delegate_task` may enforce a low `max_concurrent_children` cap (commonly 3). If the pending queue is larger than the cap, split delegation into batches instead of attempting one oversized call.
   - Post and verify finished PR results before starting the next batch when that reduces user wait time; do not hold completed approvals until the entire queue finishes.
   - In scheduled runs with finite tool budget, treat each completed current-head review as a unit of work: once the body/action is ready and the final head/review-duplication check passes, submit and verify that PR before spending more calls drafting additional PR bodies. Avoid accumulating several unposted approval/request-change bodies; a tool-call cutoff after drafting but before posting wastes the review and leaves the queue unchanged.
6. Do not let one slow or blocked PR prevent reporting already-finished PRs.
7. After each batch and again before the final “queue clear” message, re-run `scripts/list_pending_prs.sh --json`. New PRs can enter the pending queue while the batch is running; process any newly discovered PRs with the same guardrails until the live queue is empty. If the live queue grows near the end of a long run and tool/time budget is low, do **not** create a `Reviewing` thread unless there is enough budget to make meaningful review progress; instead report the newly discovered PR as still pending. See `references/live-queue-budget-exhaustion.md`.
8. If delegated reviewers time out or become too slow, do not abandon the PR or wait indefinitely. Recover in the parent/orchestrator by gathering compact live evidence with `gh` (metadata, diff or focused diff, checks, comments/reviews), running a direct Claude CLI compact prompt for Reviewer B when needed, completing the Reviewer A synthesis in the parent, then re-checking the head and posting/verifying the formal review.
   - Important: a timed-out delegate may still finish side effects after the parent sees the timeout, even if it was instructed not to post. Before the parent posts any recovered verdict, always re-query live reviews/comments for the current head and skip duplicate posting if a current-head `poom` decision appeared during recovery.
   - In scheduled cron runs, first re-run the pending queue script and verify original + newly listed PRs through the pulls reviews API before doing more review work. A timeout can coincide with late delegate review posts, raw-queue shrinkage, process-blocked current-head approvals that still remain listed, or a new PR entering the queue. See `references/scheduled-timeout-and-late-side-effects.md`.
   - If reviewer lanes completed and a formal review body was drafted, but the final pre-submit guard detects that the PR head moved, do **not** post the stale body. Refresh the PR view/diff/checks/reviews/comments, force-reset the checkout, compare `OLD..NEW`, revalidate whether the finding still exists on the new head, rewrite the body with the current head SHA, then re-run the duplicate-current-head gate before posting. See `references/head-moved-after-drafted-review-sequential-drain.md`.

### Mandatory per-PR guardrail review

For every PR that is not skipped, follow `pr-review-guardrails` fully:

- Reviewer A: OpenAI Codex / GPT-5.5 lane.
- Reviewer B: direct Claude CLI lane (`claude -p`, no ACP).
- No Claude ACP.
- No fallback of Reviewer B to Codex.
- Fresh GitHub state before deciding.
- Read PR conversation comments, inline review threads, prior formal reviews, and author replies before carrying forward any old blocker.
- For re-reviews, inherit `pr-review-guardrails` author-reply classification: clear + credible, clear but unimplemented, unclear/needs clarification, or disagreement needing evidence check.
- If an author reply is unclear or the acceptance/risk owner is missing, ask for targeted clarification instead of blindly repeating the old finding.
- Feature flag, experiment outcome, Terraform plan, CI, and coverage checks as applicable.
- Include internal per-PR token usage in user-facing chat/Discord/Telegram output when available, and omit it from GitHub review bodies/comments.
- GitHub review body title format: `Guardrail review — <RESULT>`.

If a PR was already reviewed today and the live head SHA is unchanged, a full re-review may be skipped only after verifying:

1. The previous verdict applies to the current head.
2. Poom already has a matching **submitted GitHub formal review decision** (`APPROVE` or `REQUEST_CHANGES`, as appropriate) on the current head.

If GitHub re-requests Poom after a previous approval disappears and the PR appears in the pending queue, treat it as fresh pending work: run or narrowly refresh the normal guardrail review and submit the normal formal GitHub review result on the current head. Do **not** skip based on old chat/local memory or aggregate `reviewDecision`; a current-head Poom decision must exist in the pulls reviews API, otherwise the next scheduled queue round will re-queue it again.

Exception: if the user explicitly asks to re-review and **supersede** Poom's prior current-head `REQUEST_CHANGES` when new evidence is now available (for example Digger plan output appeared after the old blocker), do not skip solely because the old Poom decision exists. Follow `pr-review-guardrails` and its `references/supersede-current-head-request-changes.md` pattern: verify the stale blocker is resolved, post the new formal `APPROVE`/`REQUEST_CHANGES` as appropriate, and verify through the pulls reviews API.

Important: the pending-review GitHub API can still return a PR after a failed previous run where Hermes wrote local review memory or a chat summary but never submitted the formal GitHub review. Treat a note like “already reviewed with existing current-head request-changes decision” as valid only after re-checking live formal reviews for the current head SHA.

The queue can also keep returning PRs that already have Poom's current-head `APPROVE` because they are blocked by process or merge state (`policy-bot`, stale AI-review refresh rows, branch behind base, pending checks). In that case, do **not** re-review or post duplicate approvals. Verify `reviewDecision == APPROVED` plus a Poom `APPROVED` review whose `commit_id` equals the current `headRefOid`, post/rename the per-PR thread as `Approved`, and report that it remains listed due process state. Treat the formal review API `commit_id` as authoritative even if the review body text quotes an older SHA; if that mismatch raises substantive uncertainty, do only narrow current-diff/check revalidation and still avoid duplicate posting when the current-head approval exists. See `references/approved-but-still-pending.md`.

Important distinction: `reviewDecision == APPROVED` is not itself proof that Poom submitted a current-head decision; it can be satisfied by another human or bot review while Poom's requested review is still pending. Before duplicate-gating any still-listed PR, filter the pulls reviews API for `user.login == "poom"`, `commit_id == headRefOid`, and `state in (APPROVED, CHANGES_REQUESTED)`. If that list is empty, continue the guardrail review/recovery path even when the aggregate PR `reviewDecision` is `APPROVED`. See `references/sequential-rmux-cutoff-after-drafted-approval-case.md`.

If Poom **does** have an older current-head approval but GitHub still lists Poom in `reviewRequests`, treat the live review request as authoritative: refresh enough guardrail evidence and post a normal current-head review result so the PR exits the pending queue. See `references/re-requested-review-clears-queue.md` for the exact recovery and reporting shape.

When the final live re-list contains only PRs that have verified current-head Poom decisions (`APPROVE` or `REQUEST_CHANGES`) and are still returned for process/merge reasons, do **not** say the raw GitHub pending queue is empty. Report each still-listed PR as `already reviewed on current head; process/merge-blocked` with the formal review id/commit. It is acceptable to add a concise recap such as “No unreviewed PRs remain,” but reserve the exact `No pending PRs — queue is clear ✅` message for an actually empty script result.

When a PR is skipped by the duplicate-current-head decision gate, still update the PR review memory before finishing if it exists or if the run maintains one: refresh the status-board head SHA, verdict, formal review id/state/`commit_id`, merge/process snapshot, and delivery channel. This prevents future queue runs from seeing a stale `Head reviewed:` line or old process-gate note even though the pulls reviews API proves a current-head decision. If the review body quotes an older SHA but the formal review record's `commit_id` equals `headRefOid`, record that distinction in memory instead of treating the quote as authoritative.

When a pending PR is a re-review or has old `CHANGES_REQUESTED` / inline blocker threads, do not reconstruct the old verdict from memory alone. Re-read the live conversation and classify the latest author replies using `pr-review-guardrails`. If the author gave a clear, credible product/scope/risk rationale and the current code evidence supports it, downgrade or approve rather than reposting stale request-changes. If the reply is unclear, ask the targeted clarification in the per-PR result and use `COMMENT`/chat follow-up rather than a robotic repeat blocker unless the code risk is independently concrete.

If the GitHub decision is missing but the review memory proves a current-head verdict, submit the missing decision before reporting. Reconstruct and post the same normal review body format from `${HERMES_HOME:-<home>/.hermes}/pr-reviews/<repo>-<number>.md` or project-local `.hermes/pr-reviews/<repo>-<number>.md`: verdict, why, findings/evidence, merge readiness, and next actions. Do **not** post a thin admin note like “submitting missing decision.” If the memory note lacks enough detail to reconstruct a proper body, re-run or narrowly re-validate the guardrail review instead of submitting a low-content decision. If current-head equivalence cannot be proven quickly, re-run the guardrail review. When a parent/orchestrator posts a formal review from a subagent's proposed body, patch the PR review memory afterward with the actual GitHub review id, state, `commit_id`, submitted timestamp, and post-action `reviewDecision`/merge-state snapshot; otherwise future queue runs may see only a proposed action and waste time revalidating or risk duplicate posting.

## GitHub Posting Policy

Default behavior for pending-queue runs:

- Post inline comments and a summary review when findings require author action.
- Submit a GitHub review decision for each reviewed PR when the user authorized GitHub posting:
  - No blockers / no high-priority issues → approve.
  - Blockers or high-priority issues → request changes.
- Treat `pre-commit-check`, `policy-bot:*`, and metadata checks as process notes by default unless the user explicitly asks to enforce them as blockers.

If the user says `chat-only`, `no GitHub comments`, or equivalent:

- Do not post comments.
- Do not approve/request changes.
- Still run the review and report per PR in chat.

If the user gives a conditional instruction, follow it exactly. Example: "post only if blockers" means no approve/comment when the PR is clean.

## Reporting to User: One Message / One PR

The user prefers batch PR results to be separable by PR.

### Scheduled cron delivery exception

When this workflow is run by a scheduled cron job, first check the job's delivery instruction. If it says the final response is automatically delivered (the common case), **do not** call `send_message`, create Discord messages/channels, or otherwise deliver dynamically; put the per-PR results and recap directly in the final response. Only use `send_message`/dynamic delivery when the job explicitly says it uses `deliver: local` and requires it. See `references/scheduled-cron-delivery.md` (`references/scheduled-cron-delivery.md`) for details and shell pitfalls.

Required reporting behavior:

1. Send **one user-facing message per PR** as soon as that PR finishes.
2. Do not wait for all PRs before reporting completed PRs.
3. Always include the full PR URL in every per-PR message.
4. Keep each PR's follow-up conversation separate when platform support allows it.

### Discord behavior

Default Discord pattern for batch pending reviews: **one PR = one normal Discord text channel under the `review-prs` category = one reusable lane for that PR**. This intentionally mirrors `my-open-prs` sidebar behavior instead of using bot-created public threads, because normal text channels reliably appear in the left channel list.

- If the request is in an existing PR-specific Discord thread or channel, continue there when it is clearly the same PR.
- For batch requests, create or reuse one deterministic normal text channel per PR under category `review-prs`:
  - Channel name: `<repo-name>-pr-<pr-number>` using Discord-safe lowercase/hyphen form, for example `finn-web-app-pr-4974` or `tools-pr-133`.
  - Channel topic: `<Owner>/<Repo> #<number> — <PR URL> — managed by Hermes pending-pr-review`. `#` is okay in the Discord channel **topic**; do not put `#` in the channel **name** because channel names are normalized and should remain linkable.
  - Reuse/adopt the existing channel when the same PR is reviewed again; never create duplicate channels for repeated asks.
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
- When a channel ID is known, send the per-PR final summary to `discord:<channel_id>`. Do not post the final PR result only to the parent/batch channel.
- Post a compact **channel index** message back to the original request thread/channel with one line per PR: repo/number, current status, PR URL, and Discord channel URL (`https://discord.com/channels/<guild_id>/<channel_id>`). This is still useful even though normal channels should appear in the sidebar.
- For lifecycle status, prefer messages and/or a short status prefix in the latest channel message. Keep channel names stable as `<repo-name>-pr-<pr-number>` to avoid duplicate/adoption problems. Add status categories later only if the category becomes crowded.
- On PR merge/close, delete/archive the managed PR review channel after posting any needed closure summary, matching the `my-open-prs` cleanup pattern.
- When the user asks to check, status, or clean up PR review channels, treat this as a review-channel lifecycle task, not the authored/open-PR queue. Scan the `review-prs` category, parse each PR from the channel topic (`EWA-Services/<repo> #<number>`) or fallback channel name (`<repo>-pr-<number>`), verify the live PR state with GitHub, and delete only channels whose PR is `CLOSED`/`MERGED`. Leave open PR channels untouched. Re-scan after deletion and report deleted count, failures, and remaining open review channels. Use the `my-open-prs` `discord_pr_channels.py` helper or its Discord API pattern for safe delete, but do not run `my_open_prs.py` because that script is for Poom-authored PRs.
- Do not collapse all PR results into one large Discord message unless the user explicitly asks for a digest. A compact end-of-run recap in the original request thread/channel is allowed after all per-PR channel results were delivered.
- If normal channel creation fails because the bot lacks permissions or `DISCORD_BOT_TOKEN` is unavailable, fall back to separate parent-channel messages, include the full PR URL, and explicitly mention the channel-creation limitation.
- In scheduled jobs, if parent/fallback progress is sent with `hermes send` to the exact same target as the cron auto-delivery destination, Hermes may return `skipped=true, reason=cron_auto_delivery_duplicate_target` even when the job prompt explicitly asked for parent progress/debug sends. Do not retry that same parent target in a loop and do not count it as a PR-delivery failure. Preserve the intended parent debug/progress lines in the final response recap, and continue sending per-PR results to distinct PR channels when available. See `references/cron-auto-delivery-duplicate-target.md`.

### Telegram behavior

- If the request is inside a Telegram forum topic, continue in that topic unless a PR-specific topic exists and is explicitly known.
- When PR-specific topics are available, use one topic per PR.
- If topic creation/selection is unavailable from current tools, send one separate message per PR and ask the user to reply in the desired PR-specific topic/thread for follow-up.
- Do not fan a topic-specific result into the parent group when a topic context exists.

### Per-PR message format

```text
<verdict emoji> <repo> #<num> — <title>
🔗 <pr url>

Verdict: <Approve | Needs changes | Blocked | Pass>
Models: Reviewer A: <openai-codex/gpt-5.5 or actual>, Reviewer B: <direct Claude CLI / actual / unavailable>
Token usage: Reviewer A: <tokens|unavailable>, Reviewer B: <tokens|unavailable>, parent/synthesis: <tokens|unavailable>, total: <tokens|unavailable> (internal only; not posted to GitHub)

Why:
- <top reason 1>
- <top reason 2>
- <top reason 3 if needed>

```

Continuation:

```text
Merge readiness:
- <merge-ready / not merge-ready / ready after X>

GitHub action:
- <approved / requested changes / commented / chat-only / not posted because condition was not met>
```

A compact end-of-run recap is optional, but it must not replace the per-PR messages. If sent, keep it short: repo, PR number, verdict, GitHub action, URL.

## References

- `references/deliver-local-hermes-send-cli.md` (`references/deliver-local-hermes-send-cli.md`) — when a `deliver: local` scheduled drain explicitly requires Discord output, prefer `hermes send --to ... --file ... --json` over ad-hoc `send_message_tool` imports from arbitrary Python.
- `references/cron-cutoff-recovery-after-user-waits.md` (`references/cron-cutoff-recovery-after-user-waits.md`) — operational recovery when Poom is waiting for a specific scheduled run result and the latest deliver-local output ended with cutoff/error; includes draft-body posting recovery and missing Discord delivery handling.
- `references/discord-thread-lifecycle.md` (`references/discord-thread-lifecycle.md`) — session note for the Discord batch-output correction: parent-channel per-PR messages are not enough; create/reuse one dedicated thread per PR, rename `Reviewing` → final status, and post the result inside that thread.
- `references/live-queue-budget-exhaustion.md` (`references/live-queue-budget-exhaustion.md`) — handling live queue growth near session/tool-budget limits without falsely declaring the queue clear or creating abandoned `Reviewing` threads.
- `references/tool-budget-offline-review-cutoff.md` (`references/tool-budget-offline-review-cutoff.md`) — how to report substantial offline review work when the tool/time budget stops the run before GitHub posting or final queue clearance.
- `references/tool-call-limit-final-response-deliver-local.md` (`references/tool-call-limit-final-response-deliver-local.md`) — exact local-log shape when a `deliver: local` scheduled drain hits the runtime/tool-call limit after some PRs were already reported and another PR was only partially started.
- `references/sequential-rmux-cutoff-after-next-pr-start.md` (`references/sequential-rmux-cutoff-after-next-pr-start.md`) — how to report/recover when sequential rmux drain completes one PR, starts the next PR, then hits a cutoff before synthesis/posting.
- `references/tool-call-max-after-rmux-launch.md` (`references/tool-call-max-after-rmux-launch.md`) — exact final-log/recovery shape when the platform forbids further tool calls after rmux lanes were launched for the next PR but before synthesis, GitHub posting, or per-PR delivery.
- `references/max-tool-iterations-cutoff-local-delivery.md` (`references/max-tool-iterations-cutoff-local-delivery.md`) — deliver-local final-response shape when the user/platform announces that no more tool calls are allowed after some PRs were already posted/reported and another PR may be unfinished.
- `references/max-tool-cutoff-after-completed-pr-and-relist.md` (`references/max-tool-cutoff-after-completed-pr-and-relist.md`) — final-response shape when PRs were posted/verified/reported and a live queue re-list already happened before the max-tool cutoff; preserve the captured queue snapshot and say no next PR was started if applicable.
- `references/sequential-rmux-cutoff-after-lanes-complete.md` (`references/sequential-rmux-cutoff-after-lanes-complete.md`) — how to report/recover when rmux lanes and current-head recheck completed, but cutoff happened before GitHub posting and per-PR Discord delivery.
- `references/sequential-rmux-cutoff-after-current-head-recheck.md` (`references/sequential-rmux-cutoff-after-current-head-recheck.md`) — recovery shape when one PR was fully completed/reported, the next PR has strong refreshed evidence and a final current-head/duplicate-review check, but max-tool cutoff happens before posting, memory update, per-PR delivery, or final re-list.
- `references/sequential-rmux-cutoff-after-evidence-only-start.md` (`references/sequential-rmux-cutoff-after-evidence-only-start.md`) — recovery/final-log shape when one PR was fully completed and the next PR only reached clone/fetch/evidence capture before cutoff; classify as evidence-only started, not reviewed, and require fresh head + duplicate-review checks before reuse.
- `references/reviewer-lanes-complete-before-posting-cutoff.md` (`references/reviewer-lanes-complete-before-posting-cutoff.md`) — deliver-local max-tool cutoff shape when one PR was reported, the next PR's Codex/Claude rmux lanes completed with a proposed verdict, but no GitHub review/per-PR result/final re-list happened yet; includes Claude interactive sentinel-mismatch nuance.
- `references/verified-review-before-delivery-cutoff.md` (`references/verified-review-before-delivery-cutoff.md`) — recovery when the formal GitHub review was already verified on the current head, but deliver-local per-PR messaging and/or final queue re-list were cut off.
- `references/tool-call-limit-after-completed-pr-report.md` (`references/tool-call-limit-after-completed-pr-report.md`) — local final-response shape when a PR was already posted, verified, memory-updated/reported to Discord, then the tool-call limit prevented the final live queue re-list; report completed PRs but say final queue clearance was not re-verified.
- `references/tool-call-cutoff-after-parent-evidence.md` (`references/tool-call-cutoff-after-parent-evidence.md`) — recovery/final-log shape when substantial parent evidence was gathered and reviewer lanes may have failed or stalled, but no formal GitHub review, per-PR user-facing result, memory update, or final queue re-list happened yet.
- `references/tool-call-cutoff-after-rmux-prompt-stall.md` (`references/tool-call-cutoff-after-rmux-prompt-stall.md`) — concrete sequential-rmux cutoff shape when Codex fails, interactive Claude idles at the prompt without a substantive response, parent evidence suggests a verdict, but no GitHub action/per-PR delivery/final re-list happened.
- `references/review-body-drafted-before-posting-cutoff.md` (`references/review-body-drafted-before-posting-cutoff.md`) — recovery when rmux/offline review produced a full `review_body.md`, but the run stopped before GitHub posting, verification, memory update, and per-PR delivery.
- `references/head-changed-request-changes-cutoff.md` (`references/head-changed-request-changes-cutoff.md`) — recovery shape when the parent already verified no current-head `poom` decision and drafted a complete request-changes body, but cutoff happened before posting, per-PR delivery, memory update, or final queue re-list.
- `references/head-moved-before-posting-cutoff.md` (`references/head-moved-before-posting-cutoff.md`) — recovery when substantial local review/evidence was gathered but `git ls-remote` or another live check shows the PR head moved before posting; abort stale GitHub action and report `no formal review posted` with old/new SHAs.
- `references/head-moved-after-drafted-review-sequential-drain.md` (`references/head-moved-after-drafted-review-sequential-drain.md`) — scheduled sequential-drain recovery when reviewer lanes completed and a review body was drafted, but the final pre-submit guard detects a new head; refresh evidence, compare old/new head, rewrite the body for the current head, and only then post/verify.
- `references/head-moved-before-posting-after-blocker-fix.md` (`references/head-moved-before-posting-after-blocker-fix.md`) — compact recovery pattern when a final pre-submit head check catches an author force-push that directly fixes the old-head blocker; abort the stale body, refresh `base...HEAD` and `OLD..NEW`, optionally run a compact current-head Reviewer B refresh, then duplicate-gate before posting.
- `references/sequential-rmux-cutoff-after-drafted-approval-case.md` (`references/sequential-rmux-cutoff-after-drafted-approval-case.md`) — concrete deliver-local recovery shape when rmux lanes and validation finish, an approve-level body is drafted, but tool/runtime cutoff prevents posting/reporting; also captures the `reviewDecision=APPROVED` but no current-head `poom` decision pitfall.
- `references/approved-but-still-pending.md` (`references/approved-but-still-pending.md`) — how to classify PRs that still appear in `list_pending_prs.sh` after Poom has already approved the current head because process/merge gates remain blocked.
- `references/current-head-decision-only-drain.md` (`references/current-head-decision-only-drain.md`) — scheduled sequential-drain pattern when every raw-pending PR already has a formal current-head Poom decision; skip rmux lanes, refresh stale memory head/status, still send per-PR reports plus a parent recap, and say “no unreviewed PRs remain” rather than the empty-queue string.
- `references/scheduled-timeout-and-late-side-effects.md` (`references/scheduled-timeout-and-late-side-effects.md`) — cron-run recovery when delegated reviewers time out but may still post reviews and the live queue mutates.
- `references/cron-idle-timeout-and-provider-stalls.md` (`references/cron-idle-timeout-and-provider-stalls.md`) — diagnosing scheduled-run idle timeouts caused by stale model/provider calls versus queue-script failures, plus smaller-batch mitigations.
- `references/github-search-limit-before-filtering.md` (`references/github-search-limit-before-filtering.md`) — why raw GitHub search limits must be high enough before local filtering.
- `references/rmux-cli-reviewer-lanes.md` (`references/rmux-cli-reviewer-lanes.md`) — rmux/tmux lane timeouts, output capture, polling, and duplicate-review guards.
- `references/sequential-rmux-drain-discord-progress.md` (`references/sequential-rmux-drain-discord-progress.md`) — scheduled sequential rmux drains where the job explicitly requires Discord progress/per-PR messages despite final-response auto-delivery; includes process-blocked current-head decisions and lane transport-stall reporting.
- `references/cron-start-vs-output-finalization.md` (`references/cron-start-vs-output-finalization.md`) — diagnosing apparent skipped hourly rounds where `next_run_at` advanced at start but `last_run_at`/output update only on finish.
- `references/cron-auto-delivery-duplicate-target.md` (`references/cron-auto-delivery-duplicate-target.md`) — handling `hermes send` skips when a scheduled job tries to dynamically send parent progress to the same target that will receive the cron final response.
- `references/context-compaction-after-completed-pr.md` (`references/context-compaction-after-completed-pr.md`) — recovery when context compaction/resume happens after a PR was fully posted, per-PR-delivered, memory-updated, and re-listed, but before the parent completion line was sent; send once if possible, otherwise include the skipped parent line in the final cron response.
- `references/claude-interactive-sentinel-prompt-echo.md` (`references/claude-interactive-sentinel-prompt-echo.md`) — avoid treating an echoed sentinel in an interactive Claude prompt as a real Reviewer B verdict.
- `references/sequential-rmux-claude-startup-idle-variants.md` (`references/sequential-rmux-claude-startup-idle-variants.md`) — recognize variant Claude Code startup-prompt stalls (`gh auth login`, sample prompt text, no assistant output) and recover without waiting the full lane timeout.

## Failure Handling

- If a reviewer lane fails, report the lane as unavailable and continue according to `pr-review-guardrails`.
- In interactive Claude rmux mode, do not mark Reviewer B unavailable solely because the helper appended `__CLAUDE_IDLE_WITHOUT_SENTINEL__`. If the captured pane contains a substantive current-head verdict/review and `__CLAUDE_EXIT:0__`, treat the lane as usable and record a sentinel-mismatch transport note. Mark it unavailable only when the output is prompt echo/idle noise or lacks a substantive review. If the pane is just the Claude Code startup screen/TUI footer with `gh auth login` and a sample prompt (the exact sample text varies, e.g. `Try "how do I log an error?"`), kill the rmux session, record Reviewer B as transport-stalled/unavailable, and continue parent synthesis instead of waiting for the full timeout.
- Conversely, do not accept a successful sentinel/exit marker when the exact sentinel was included in the prompt and the captured output is only prompt echo. This is a sentinel prompt-echo false-positive: ignore it, rerun with a shorter prompt or out-of-band sentinel instruction, and use only substantive reviewer output. See `references/claude-interactive-sentinel-prompt-echo.md`.
- If a scheduled cron run fails with `idle for 601s` / idle timeout after the last successful tool call, diagnose provider/model stalling separately from queue discovery: verify `scripts/test_list_pending_prs.sh` and `scripts/list_pending_prs.sh --stats-json`, inspect gateway logs around the run for stale non-streaming API calls or `APIConnectionError`, and report whether Discord delivery warnings are only a visibility/routing issue. Prefer shrinking the batch size (often one PR per tick) and immediate per-PR post/verify over increasing idle timeout. See `references/cron-idle-timeout-and-provider-stalls.md`.
- For scheduled pending-review runs where Hermes `delegate_task` / in-process model calls stall or Claude Code print mode (`-p`) is unavailable for the subscription plan, use sequential rmux/tmux reviewer lanes: launch Codex CLI and direct Claude Code CLI in separate `rmux` sessions with shell/Python timeouts, redirect/capture each lane to per-PR output files, poll with `rmux has-session` and file reads, then synthesize/post from the parent after final GitHub head verification. For Claude Reviewer B, prefer `scripts/rmux_claude_interactive_reviewer.py`, which drives interactive `claude --tools ''` without `-p` by pasting the prompt into the TUI and waiting for a sentinel/idle prompt. Do not use this to skip guardrails; it is only an execution transport for Reviewer A/B.
  - Timeout binary portability: this cron can run on macOS where `/usr/bin/timeout` does not exist; probe with `command -v timeout || command -v gtimeout` and use the discovered path (commonly `/usr/local/bin/timeout`) or a Python timeout wrapper. Do not hardcode `/usr/bin/timeout` in rmux launcher snippets.
  - Codex CLI model compatibility can differ by account type. If `codex exec` exits with an API error such as `model is not supported when using Codex with a ChatGPT account`, do not abandon Reviewer A immediately. Relaunch the rmux lane with an explicitly supported GPT-5.5 model (for example `codex exec --model gpt-5.5 ...`) or run a quick one-line model probe before the real review. Record the first lane as a transport/model-selection failure, not a review finding.
  - For compact evidence-only prompts, tell both lanes not to use tools and include a completion sentinel for Claude. A successful Claude interactive lane should show the sentinel plus `__CLAUDE_EXIT:0__`; if it idles at the prompt without a substantive answer, mark that lane unavailable instead of treating pasted prompt text as reviewer output. If the captured Claude pane shows only the pasted prompt/TUI footer or a tool/auth prompt such as `gh auth login`, kill the rmux session, optionally retry once with a shorter evidence-only prompt, and then proceed with parent synthesis from refreshed GitHub/local evidence if no substantive verdict appears.
- If a delegated PR review times out after substantial work, salvage it rather than starting over blindly: use the partial known state only as hints, refresh live GitHub data, build a compact evidence packet (`gh pr view`, focused diff, checks, recent comments/reviews), run direct Claude CLI with `--tools ''` for Reviewer B if practical, and complete the review/posting from the parent with a final head re-check.
- If a single PR fails to review due to checkout/API/test failure, report that PR separately with the failure reason and continue other PRs.
- When local Python tests fail in repos with multiple Lambda/function directories that each import as `lambda_function`, check for `sys.modules`/wrong-handler collision before classifying it as a PR blocker. Re-run affected suites in separate pytest processes and use `pr-review-guardrails/references/python-lambda-module-name-collision-tests.md` for the pattern.
- If a workflow is still `in_progress` but one required job has already failed, and `gh run view --log-failed` refuses logs until the whole workflow completes, use `references/github-actions-job-logs-while-run-active.md` (`references/github-actions-job-logs-while-run-active.md`) to fetch the completed job log through the Actions job logs API before classifying the failure as code blocker vs process/merge-readiness.
- If delivery of a per-PR result fails, retry explicit delivery once before moving on.
- Never silently drop a PR result because a batch/final summary failed.

## Common Pitfalls

1. **Using this as a replacement for guardrails.** This skill only orchestrates many PRs; each actual review must use `pr-review-guardrails`.
2. **One giant batch summary.** The user wants one message per PR so follow-ups can continue separately.
3. **Plain PR labels.** Labels like `pr123` collide across repos; always include repo slug.
4. **Posting GitHub decisions when chat-only was requested.** Honor chat-only and conditional posting exactly.
5. **Skipping current-head verification.** A same-day review note is not enough; verify the live head and current GitHub review decision.
6. **Treating process-blocked approved PRs as fresh review work.** If the queue still lists a PR but Poom already has an `APPROVE` on the current head, do not post a duplicate review. Report it as already approved/current-head and still listed because of process or merge blockers.
7. **Claude ACP.** Do not use Claude ACP; use direct Claude CLI for Reviewer B.
8. **Oversized parallel delegation.** Do not assume all pending PRs can be delegated in one call. If `delegate_task` rejects the batch with `Too many tasks` / `max_concurrent_children`, immediately split into smaller batches and continue; this is a routing limit, not a review failure.
9. **Declaring victory before re-listing the queue.** Pending queues are live: after posting reviews for all initially discovered PRs, new PRs may appear. Always run the list script again and only say `No pending PRs — queue is clear ✅` after the final live list is empty. If the final list is non-empty but every returned PR already has a verified current-head Poom decision, say “No unreviewed PRs remain” and list the process-blocked PRs instead of falsely claiming the raw queue is empty. If a new PR appears when the session is near a tool/time budget limit, explicitly report it as still pending rather than starting a `Reviewing` thread that cannot be completed. If tool budget is exhausted immediately after posting/verifying a review but before the final queue re-list, report the exact completed PR actions and review ids, and say that final live queue clearance was not verified instead of implying the queue is clear. If the runtime/user interrupts with a tool-call-limit message, do not attempt more delivery or queue checks; the final response should include the last live queue snapshot, every verified GitHub action/review id, and the explicit caveat “final live queue clearance was not re-verified.” In `deliver: local` sequential-drain jobs, also distinguish PRs that were fully reported to Discord from PRs only discovered or duplicate-probed but not yet given their required per-PR/user-facing message; label the latter as “still needs per-PR report/processing” rather than implying the workflow completed them. If sequential rmux drain already completed and reported one PR, then created/reused a channel, fetched evidence, or launched rmux lanes for the next PR before cutoff, use `references/sequential-rmux-cutoff-after-next-pr-start.md`: mark that next PR explicitly as unfinished, list lane/session/output paths if known, and state `no GitHub review posted` / `no final per-PR result sent` for it. If live head checks show the PR branch moved after local evidence/reviewer work but before posting, use `references/head-moved-before-posting-cutoff.md`: treat the evidence as stale, record old/new SHAs, do not post a saved body, and report `GitHub action: none / no formal review posted`. If the head moves after a full draft exists but there is still enough budget to recover, use `references/head-moved-after-drafted-review-sequential-drain.md`: abort the stale body, refresh the new head/reviews/checks/threads, compare `OLD..NEW`, rewrite the formal review so resolved blockers are marked stale and only current-head blockers remain, then re-run the duplicate-current-head gate before posting. If the next PR only reached clone/fetch/artifact capture before cutoff (no reviewer lanes, no synthesis, no GitHub action, no per-PR result), use `references/sequential-rmux-cutoff-after-evidence-only-start.md`: classify it as **evidence-only started**, not reviewed or failed, and require a fresh current-head + duplicate-review gate in the recovery run. If the platform/user explicitly says the maximum tool-calling iterations have been reached, use `references/max-tool-iterations-cutoff-local-delivery.md`: stop all further delivery/verification attempts and produce only a local recovery log with completed PRs, unfinished PRs, last live queue snapshot, and the caveat `final live queue clearance was not re-verified` unless a final re-list already happened. If a PR-specific Discord channel was created but review work was not started or completed before cutoff, include the channel id/URL in the local cutoff log, but still mark that PR as **not reviewed / no GitHub action taken**; channel creation alone is not a user-facing PR result. If substantial offline review work completed but GitHub posting did **not** happen before cutoff, say so per `references/tool-budget-offline-review-cutoff.md`; never label the PR as `approved/requested changes` unless the pulls reviews API confirms the formal decision on the current head. If both rmux reviewer lanes completed and the parent even rechecked the current head but cutoff happened before GitHub posting/per-PR Discord delivery, use `references/sequential-rmux-cutoff-after-lanes-complete.md`: report the proposed verdict as **not posted**, include the last live snapshot, and treat the PR as unfinished until a recovery run revalidates and posts/reports it. If the cutoff occurs after one PR was fully reported and the next PR's reviewer lanes completed but before posting/user-facing delivery/final re-list, use `references/reviewer-lanes-complete-before-posting-cutoff.md`: include the completed PR's review id/messages, the unfinished PR's lane output paths and proposed verdict, and explicitly say `GitHub action: none / no formal review submitted` plus `final live queue clearance was not re-verified`. If a complete `review_body.md` was drafted but the cutoff happened before `gh pr review`, verification, memory update, or per-PR Discord delivery, use `references/review-body-drafted-before-posting-cutoff.md`: report the body as a draft path only, explicitly say `GitHub action: none / no formal review posted`, and make the recovery run re-fetch head + duplicate-review state before posting the saved body. If the formal review **was** posted and verified before the cutoff but the deliver-local per-PR message, parent index, memory update, or final queue re-list did not happen, use `references/verified-review-before-delivery-cutoff.md`: do not duplicate the GitHub review; first verify current-head review id/commit, then complete the missing per-PR user-facing delivery and clearly say final live queue clearance was not re-verified unless you re-list it.
10. **Batch-drafting without posting.** In cron runs, do not draft multiple approval/request-change bodies and defer all GitHub submissions until the end. Post and verify each ready PR immediately after its final head/duplicate-review check, then move to the next PR. If cutoff happens, it is better to have one verified review id plus an honest unfinished list than several unposted draft bodies and no queue progress.
11. **Letting subagent timeouts stall the batch.** A timed-out delegate is not automatically a failed review. If enough public evidence can be refreshed, finish the review in the parent with focused `gh` queries, a compact direct-Claude Reviewer B prompt, head verification, and normal GitHub review posting. However, do not assume a timed-out child made no side effects: before posting from the parent, re-check current-head reviews/comments because a runaway delegate may have submitted the missing formal review after timeout.
12. **Skipping user-facing reports for duplicate-gated PRs.** In deliver-local sequential-drain jobs, a PR skipped because Poom already has a current-head formal decision still needs the same user-visible per-PR Discord result plus a parent/fallback index line. Do not silently skip it after updating memory. If all final raw-pending PRs are duplicate-gated/process-blocked, report “no unreviewed PRs remain” and list them; do not send the exact empty-queue string unless the script result is empty. See `references/current-head-decision-only-drain.md`.
13. **Cron delivery conflicts with Discord routing.** The Discord/channel routing rules are for interactive gateway runs. In scheduled cron runs where the wrapper auto-delivers the final response, do not create/send Discord messages unless the job explicitly asks for dynamic delivery; use final-response per-PR sections instead.
13. **Orphaned rmux reviewer panes after cutoff.** If Hermes hits max tool iterations/runtime cutoff while an interactive Claude wrapper is polling, the Python wrapper may be terminated before its `finally` block kills the rmux session. A stale `claude --tools ''` pane may then sit at the Claude prompt for hours, sometimes with child MCP servers such as Playwright. Before declaring a pending-review cron currently running, distinguish these orphan panes from a live Hermes cron process. Inspect `/tmp/pending-pr-review-rmux/.../rmux/claude.out`, `rmux capture-pane -t <session> -p`, and the cron output file. If the pane is just the startup prompt/no substantive review and the corresponding run already logged it as stalled/unavailable, kill only that stale rmux session and record the root cause.
14. **Pipe-to-interpreter security blocks.** Non-interactive shells may block `bash ... | python3 ...` as unsafe. When post-processing queue JSON, write the JSON to `/tmp/*.json` first and run Python over the saved file.
15. **Misdiagnosing cron idle timeouts as queue bugs.** If a scheduled run fails after 600s idle and gateway logs show stale non-streaming model calls or `APIConnectionError`, the queue script may be healthy. Verify script tests and `--stats-json` first, then mitigate by shrinking the batch and avoiding long unstimulated model/delegate waits. Do not blindly rewrite filters or increase the idle timeout as the first fix.

## Verification Checklist

- [ ] Pending PR list fetched from live GitHub data
- [ ] Drafts, bots, and automerge PRs filtered out
- [ ] Empty queue reported if applicable
- [ ] Queue re-listed after posting reviewed PRs; any newly pending PRs processed before final clear message
- [ ] PRs still listed after current-head Poom approval classified as process/merge-blocked approved PRs, not duplicated reviews
- [ ] Each PR uses repo-qualified task/worktree labels
- [ ] Each non-skipped PR reviewed using `pr-review-guardrails`
- [ ] For re-reviews, live comments/inline threads/author replies checked and classified before repeating old findings
- [ ] Current head SHA checked before each verdict/action
- [ ] Internal token usage included in per-PR user-facing output when available and omitted from GitHub comments/reviews
- [ ] If using rmux/tmux external reviewer lanes, follow `references/rmux-cli-reviewer-lanes.md` for timeouts, output capture, polling, and duplicate-review guards
- [ ] GitHub posting follows user's authorization/conditions
- [ ] Discord per-PR results used one normal text channel per PR under `review-prs` when possible, with deterministic reuse by `<repo-name>-pr-<pr-number>`
- [ ] One user-facing message sent per PR
- [ ] Full PR URL included in every per-PR message
- [ ] Optional recap does not replace per-PR reporting
