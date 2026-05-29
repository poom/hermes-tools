# Tool-call cutoff after parent evidence, before posting

Use this when a sequential pending-review drain has completed substantial parent/orchestrator evidence gathering for a PR, but the platform announces that no more tool calls are allowed before the formal GitHub review, per-PR user-facing delivery, memory update, or final queue re-list.

## Required final-response shape

Do **not** imply the PR was reviewed, approved, or requested-changes unless the pulls reviews API already verified a current-head formal review by `poom`.

Report locally:

- Completed PRs that were already posted/verified/reported, including review ids and delivery targets.
- The unfinished PR, with:
  - PR URL/title.
  - Current head SHA last verified.
  - Evidence gathered so far.
  - Reviewer lane status/output paths if known.
  - Proposed/likely verdict only as `likely` or `evidence points to`, never as a completed GitHub action.
  - Explicit `GitHub action: none / no formal review submitted`.
  - Explicit `No per-PR user-facing result sent` when applicable.
- Last live queue snapshot, if known.
- Caveat: `final live queue clearance was not re-verified` unless a final live queue re-list already happened.

## Recovery run

A later recovery run must not post from the stale local conclusion directly. It must first:

1. Re-fetch the pending queue.
2. Re-fetch PR head/reviews/checks/comments/review threads for the unfinished PR.
3. Verify whether any late reviewer/subagent side effect posted a current-head `poom` decision.
4. If no current-head decision exists, revalidate the key evidence against the current head, then submit the normal full review body/action.
5. Send the required per-PR user-facing result and parent index/update after posting/verifying or duplicate-gating.

## Common example

Parent evidence may be strong enough to lean `REQUEST_CHANGES` (for example a documented 5-minute timeout but current config sets a global 180000 ms timeout and current checks fail with `Test timeout of 180000ms exceeded`). Still classify the PR as unfinished at cutoff until the formal GitHub review is posted and verified, or a current-head duplicate decision is found.
