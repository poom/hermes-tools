# Head moved after draft; partial fix changes verdict body

Use this when a PR head changes during the final pre-post duplicate/current-head check after a review body has already been drafted.

## Pattern

1. **Abort the stale post immediately.** Do not submit the saved review body against the new head, even if the likely verdict still seems similar.
2. **Refresh live state:** `gh pr view`, pulls reviews API, checks, review comments/threads, and the current `base...HEAD` diff for the new head.
3. **Compare old head to new head:** save `OLD..NEW` stat/patch and inspect whether each drafted blocker was fixed, changed, or made stale.
4. **Re-run the duplicate-current-head gate** for `user.login == "poom"`, `commit_id == headRefOid`, and `state in (APPROVED, CHANGES_REQUESTED)` before any post.
5. **Rewrite the formal review body, not just the SHA.** If the new push resolved one blocker but left another, explicitly say which prior finding is stale/resolved and request changes only for the remaining concrete risk.
6. **Post only after a second current-head check** confirms the reviewed head is still current, then verify through the pulls reviews API.
7. **Report the abort/revalidation in user-facing output.** Mention that the branch moved, the stale body was not posted, the new head was reviewed, and the final review id/commit.

## Why this matters

A force-push or quick fix can invalidate part of a drafted request-changes body. Posting the old body creates stale feedback and can duplicate already-resolved blockers. The correct outcome may still be `REQUEST_CHANGES`, but the evidence and wording must be current-head scoped.

## Minimal evidence to preserve

- Old and new head SHAs.
- `OLD..NEW` diff stat or patch path.
- Refreshed PR metadata/reviews/checks paths.
- Which blockers were resolved/stale vs still open.
- Final formal review id/state/commit from the pulls reviews API.
