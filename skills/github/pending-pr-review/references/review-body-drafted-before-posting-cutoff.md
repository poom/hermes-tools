# Cutoff after review body is drafted but before posting

Use this recovery pattern when a scheduled `pending-pr-review` sequential rmux drain has completed enough review work to draft a formal GitHub review body, but the run stops before the parent posts/verifies the formal review and sends the required per-PR user-facing result.

## Recognition signals

- Reviewer lanes completed or one lane completed and the other was explicitly unavailable/aborted.
- A proposed verdict and full `review_body.md` exist under `/tmp/pending-pr-review-rmux/<repo>-<pr>/`.
- The final head/duplicate gate may have been partially checked, but no `gh pr review` verification output exists for the current head.
- No per-PR Discord/Telegram result was sent, or only a local final log mentions the PR.

## Required final-log wording

Do **not** say the PR was approved/requested-changes unless the pulls reviews API confirms a formal current-head review. Report it as unfinished:

- `proposed verdict: <Approve|Needs changes> (not posted)`
- `GitHub action: none / no formal review posted`
- `User-facing delivery: not sent`
- `review body draft: <path>`
- `final live queue clearance was not re-verified` unless a final queue relist actually happened.

## Recovery steps for the next run

1. Re-fetch live PR state: head SHA, reviewDecision, mergeStateStatus, checks, reviews, review threads/comments.
2. If the head changed since the draft, do **not** post the saved body blindly. Revalidate the delta and update the body first.
3. Check the pulls reviews API for a current-head `poom` formal decision; skip duplicate posting if one appeared after the cutoff.
4. If no duplicate exists and the body is still current, post the saved full review body with the intended action (`APPROVE` or `REQUEST_CHANGES`).
5. Verify the review via pulls reviews API and record id/state/`commit_id`.
6. Update review memory with the posted review metadata and merge/process snapshot.
7. Send the required per-PR user-facing result to the PR channel/fallback target, then send the compact parent index/update.
8. Re-list the pending queue before declaring queue state.

## Pitfalls

- A saved `review_body.md` is only a draft until the GitHub API confirms a formal review id attached to the current head.
- Do not let a local cron final response be the only user-facing result in `deliver: local` jobs; after recovery, send the per-PR message explicitly.
- Do not call the queue clear if the cutoff happened before the final queue relist.
