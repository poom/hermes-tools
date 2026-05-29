# Scheduled timeout recovery and late side effects

Use this when a scheduled `pending-pr-review` run delegates PR reviews and one or more delegate tasks time out.

## Pattern observed

A timed-out reviewer delegate can still finish useful work and may even submit a formal GitHub review after the parent sees the timeout. Meanwhile, the live pending queue can change: reviewed PRs may disappear, process-blocked current-head approvals may remain listed, and new PRs may enter the queue.

## Recovery sequence

1. Immediately re-run the live queue script and save the JSON to a temp file before deciding what remains unreviewed.
2. For every PR from the original batch and the new live queue, query live PR state and pulls reviews API:
   - `gh pr view N --repo OWNER/REPO --json headRefOid,reviewDecision,mergeStateStatus,state,title,url`
   - `gh api repos/OWNER/REPO/pulls/N/reviews --paginate`
3. Treat a current-head `poom` `APPROVED` or `CHANGES_REQUESTED` review as authoritative even if the parent did not receive a delegate summary.
4. Do not duplicate a current-head decision. Report the PR as `already reviewed on current head; process/merge-blocked` when the raw queue still lists it.
5. Only recover/re-review PRs that lack a verified current-head Poom decision and only if there is enough tool/time budget to complete freshness checks, Reviewer B, posting, and verification.
6. If a new PR appears near the end of the run and budget is tight, report it as still pending rather than starting an abandoned review.

## Reporting

In the final scheduled-cron response, distinguish:

- `raw pending queue` — what the script still returns;
- `unreviewed PRs` — items without a verified current-head Poom decision;
- `process/merge-blocked approvals` — items still listed despite current-head approval.

Only use the exact `No pending PRs — queue is clear ✅` message when the raw script result is empty.
