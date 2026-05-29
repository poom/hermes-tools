# Tool-budget cutoff after offline pending-PR review

Use this when a scheduled pending-pr-review run completes substantial review work but hits the tool-call/time budget before GitHub posting and final queue clearance.

## Pattern observed

A cron run reviewed multiple PRs locally/offline, refreshed live queue state, and wrote review memory, but did not submit GitHub review decisions before the tool budget stopped. The final queue still contained both genuinely unreviewed PRs and a process-blocked PR that already had a current-head Poom approval.

## Required behavior

- Prefer prevention: do not batch up multiple completed formal review bodies for end-of-run posting. As soon as one PR has a synthesized verdict, complete the final head/duplicate-review check, submit the GitHub decision, verify the review id/commit via the pulls reviews API, update review memory, and only then continue to the next ready PR.
- Do **not** imply the workflow completed or that GitHub actions were taken.
- For every PR, explicitly distinguish:
  - `reviewed offline / approve-level` vs. `formal GitHub review posted`.
  - `no current-head Poom decision found` vs. `current-head Poom approval/request-changes verified`.
  - `code review clean` vs. `process/check/merge gates still blocking`.
- If posting did not happen, say `GitHub action: not posted before tool budget ended` (or equivalent). Do not say `approved` or `requested changes` unless the review API confirms the submitted decision.
- Re-listing the queue before cutoff is useful evidence, but if the final live queue is non-empty, do not use the exact clear-queue sentence.
- For already-approved process-blocked PRs discovered during the final queue relist, verify with the pulls reviews API using `commit_id == headRefOid`; report them as `already approved on current head; still listed due process/merge gates` and avoid duplicate approvals.
- If review memory was written but no GitHub decision was posted, note that a follow-up run can use the memory only after rechecking the live head and formal reviews.

## Compact final wording

```text
Final queue was not clear. I reviewed <PRs> offline but did not post GitHub decisions before the tool budget ended.

<repo> #<num> — <title>
Verdict: Approve-level / Needs changes / Already reviewed on current head
GitHub action: not posted before tool budget ended | existing current-head Poom APPROVE verified <review id>
Merge readiness: <code-ready but process-blocked / not ready because ...>
```
