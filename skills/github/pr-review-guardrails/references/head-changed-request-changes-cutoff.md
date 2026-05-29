# Head changes after drafting request-changes, with limited tool budget

Use this when a blocker-level review body has been drafted, but the PR head changes immediately before posting and the session/tool budget is close to exhausted.

## Pattern

1. **Abort the stale post.** If the live `headRefOid` differs from the reviewed SHA, do not submit the drafted `REQUEST_CHANGES`/`APPROVE`, even when the finding looked solid on the old head.
2. **Inspect the delta before deciding.** Compare `OLD_HEAD..NEW_HEAD` plus the live `base...HEAD` diff for the specific blocker area. The author may have force-pushed a fix for the exact blocker.
3. **Classify the new state explicitly.** Common outcomes:
   - blocker fixed and no new blocker found → draft/post an updated approve-level review after final head check;
   - blocker partially fixed but a related gate still fails with a new concrete reason → continue as current-head needs-changes only after validating that new reason;
   - insufficient budget to validate the new head → do not post; report the PR as still pending/unfinished and include the last reviewed SHA, new SHA, and why posting was withheld.
4. **Do not recycle old inline comments blindly.** Line numbers and issue substance may be stale. Re-query/refresh review comments if you will post on the new head.
5. **For cron runs, prefer honesty over queue progress.** If the head changed and the tool-call limit is near, final output should say `not posted — head changed before submission; current-head review not completed` rather than implying approval/request-changes.

## Example wording

> Not posted — the PR head changed from `<old>` to `<new>` during final verification. The old drafted blocker may have been addressed, but current-head validation was not completed before cutoff, so the PR remains pending.
