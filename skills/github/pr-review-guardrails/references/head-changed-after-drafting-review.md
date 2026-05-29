# Head changed after drafting a review body

Use this when a PR head changes after you have completed synthesis or drafted a formal GitHub review body, but before the review is posted.

Concrete pattern: EWA-Services/Tools #147. A current-head re-review at `d9f723f` found the launch-error fix correct but requested changes because required Ruff/pre-commit checks failed on `runner.py` and `secrets.py`. Before posting, the author pushed `5edb00f` applying Ruff format. The correct recovery was to abandon the stale `REQUEST_CHANGES` body, refresh the PR head/checks, inspect the tiny `d9f723f..5edb00f` delta, rerun focused local validation plus direct Claude CLI Reviewer B over the new evidence, and then post a current-head `APPROVE`.

## Required workflow

1. Immediately before posting, sample `headRefOid` again. If it differs from the reviewed/drafted head, do **not** post the old body.
2. Fetch/reset to the new PR head with a force refspec if needed.
3. Inspect both:
   - previous-reviewed-head `..` new-head delta
   - live `origin/<base>...HEAD` PR diff for the affected paths
4. Re-read recent comments/reviews/checks. Authors often push exactly the fix you were about to request.
5. Rerun focused validation for the changed area and any previously failing gate.
   - For formatting-only fixes: `git diff --check`, formatter check, linter check, and the relevant narrow test suite are usually enough.
6. Run compact direct Claude CLI Reviewer B over the updated evidence when practical.
7. Draft a new formal review body for the new current head. Do not reuse a stale request-changes body except as historical context.
8. Post only after a second head sample confirms the head is still unchanged.
9. Verify the posted review through the pulls reviews API with `commit_id == headRefOid`.
10. Update review memory with both the abandoned stale verdict and the posted current-head verdict so future runs understand why the decision changed.

## Pitfall

Never submit `REQUEST_CHANGES` for a formatting/check failure after the author has pushed a format-only fix, even if the old body was already written. Stale negative reviews create avoidable review churn and can keep the pending queue noisy.
