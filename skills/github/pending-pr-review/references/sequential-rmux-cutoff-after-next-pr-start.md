# Sequential rmux cutoff after starting the next PR

Use this when a scheduled `pending-pr-review` run completed one PR, re-listed the queue, then started the next PR but hits a Hermes/tool-call cutoff before synthesis/posting.

## Pattern

1. **Do not imply the next PR was reviewed.** Channel creation, metadata fetches, checkout, or launching rmux reviewer lanes are not a user-facing review result.
2. **Preserve the completed PR separately.** Report every completed GitHub action with review id/state/commit and where the PR result/index messages were sent.
3. **Label the in-progress PR as unfinished.** Include:
   - PR URL and channel id/URL if created.
   - Evidence gathered (metadata/diff/checks/reviews/threads/checkout) only as internal progress.
   - Reviewer lane session names/output paths if lanes were launched.
   - Explicit `no GitHub review posted` and `no final per-PR result sent`.
4. **Do not claim queue clear.** Say final live queue clearance was not re-verified after starting the unfinished PR.
5. **Next run recovery:** first re-run the live queue script, then check whether any rmux lanes from the interrupted PR finished and whether any current-head `poom` formal review appeared before posting from recovered evidence.

## Why

In sequential drain mode the unit of completion is a posted/verified PR result plus user-visible per-PR report. Starting the next rmux review improves throughput, but a tool-call cutoff can leave detached reviewer sessions or partial evidence. Future runs must recover from live GitHub state and durable output files rather than treating the partial start as a completed review.
