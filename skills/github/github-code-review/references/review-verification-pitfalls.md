# Review verification pitfalls

Use this reference when a PR review has been submitted but GitHub state looks stale or contradictory.

## Verify the review really posted

`gh pr review` can exit 0 while `gh pr view --json latestReviews` is not the best evidence of the new review. The `latestReviews` projection can omit review URLs and can collapse bot/user identities in surprising ways.

After posting, verify via the Pull Request Reviews API:

```bash
gh api repos/OWNER/REPO/pulls/PR/reviews \
  --jq '.[] | {id,state,user:.user.login,commit_id,submitted_at,html_url} | @json' | tail -10
```

Use the returned `html_url` / `id` in the user summary.

## Review decision can remain stale after your approval

If `reviewDecision` still says `CHANGES_REQUESTED` after your approval, do not assume your review failed. Check the reviews list and unresolved threads. The decision may remain blocked by another reviewer's older changes-requested review or by PolicyBot requiring a specific owner/team approval.

Report this distinction explicitly:

- `Approved current head; my review id ...`
- `reviewDecision still CHANGES_REQUESTED because <reviewer/policy> remains outstanding`

## Already-merged PRs

If the PR is already `MERGED`, still inspect and validate normally when the user asks for a review. GitHub may still accept a formal review after merge. If posted, label it as `post-merge` in the summary so the user understands it cannot affect merge gating.

## Stale inline threads

When a blocker is fixed, resolve the specific review thread only after verifying the current code. Use GraphQL `resolveReviewThread`, then re-query unresolved count before finalizing.
