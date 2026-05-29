# Head moved after drafting a review in sequential rmux drain

Use this when a scheduled `pending-pr-review` run has completed reviewer lanes and drafted a formal review body, but the final pre-submit guard finds that the PR head SHA changed before `gh pr review`.

## Required recovery pattern

1. **Do not post the stale body.** Treat the drafted body as evidence/hints only, even if the expected verdict seems obvious.
2. **Refresh live state for the new head:**
   - `gh pr view <num> --json headRefOid,reviewDecision,mergeStateStatus,title,body,baseRefName,headRefName`
   - `gh api repos/<owner>/<repo>/pulls/<num>/reviews --paginate`
   - `gh api repos/<owner>/<repo>/pulls/<num>/comments --paginate`
   - review threads via GraphQL when available
   - force-fetch the PR ref and reset the disposable checkout to the new head.
3. **Compare old head to new head** with `git diff --stat OLD..NEW` and, when needed, `git diff OLD..NEW`.
   - If the delta only touches unrelated metadata/template/base-refresh files and the live `base...HEAD` PR-owned diff still contains the finding, a narrow revalidation is enough.
   - If the delta touches the finding, tests, Terraform/Digger scope, or reviewer evidence, re-run or materially refresh the guardrail review before posting.
4. **Re-check duplicate decisions on the new head.** Query the pulls reviews API and require `user.login == "poom"`, `commit_id == headRefOid`, and `state in (APPROVED, CHANGES_REQUESTED)` before skipping as already reviewed.
5. **Rewrite the formal review body for the new head.** Mention the head movement and current-head SHA when useful; remove stale SHA claims from the old draft.
6. **Submit only after one more current-head guard.** Immediately before `gh pr review`, re-query `headRefOid`; abort again if it changed.
7. **Verify the posted review** through the pulls reviews API, trusting the review record's `commit_id` over any SHA quoted in the body.
8. **Update review memory and user-facing result** with:
   - old head and new head,
   - whether evidence was narrowly refreshed or fully re-run,
   - posted review id/state/commit,
   - final queue re-list result.

## Concrete example

A scheduled sequential drain reviewed `EWA-Services/Infrastructure` #4744 at `e12170d...` and drafted `REQUEST_CHANGES` because `digger.yaml` enabled `database-staging` while the PR body said that Digger scope was intentionally deferred due overlapping staging RDS security-group ownership. The pre-submit guard found the head had moved to `20ba9cf...`.

The recovery was:
- abort the old review body,
- force-fetch/reset the checkout,
- regenerate PR view/diff/checks/reviews/comments,
- compare `OLD..NEW` and see only `.github/pull_request_template.md` changed,
- confirm the refreshed `base...HEAD` diff still added `database-staging`, the PR body still contradicted that scope, and current-head review comments still flagged the same SG ownership blocker,
- rewrite the request-changes body for `20ba9cf...`,
- re-query for a current-head Poom decision,
- submit and verify the `CHANGES_REQUESTED` review on the new head.

This avoided posting a stale review while still finishing the PR in the same cron run.
