# Volatile PR Heads During Review

Session pattern captured from Tests #197 (2026-05-14): the PR was force-pushed/rebased multiple times while review was in progress. The diff stayed semantically identical, but the head SHA changed from `9eb8979` to `b071ae72` to `7c67215` before posting.

Reusable handling:

1. Treat any head-SHA change after reviewer lanes complete as a stale-output risk, even if the diff appears small.
2. Refresh PR metadata, comments, reviews, checks, and diff.
3. Force-fetch the PR ref if the branch was rebased:
   ```bash
   git fetch origin master +pull/$PR_NUMBER/head:refs/remotes/origin/pr-$PR_NUMBER
   git checkout -B review-pr-$PR_NUMBER origin/pr-$PR_NUMBER
   ```
4. Compare the refreshed diff to the reviewed diff. If materially changed, rerun the relevant reviewer lanes. If semantically identical (same files/same tag-only or formatting-only diff), document that equivalence and narrowly revalidate.
5. Before posting `APPROVE` or `REQUEST_CHANGES`, sample the head SHA twice with a short delay and abort if it changes:
   ```bash
   HEAD1=$(gh pr view "$PR_URL" --json headRefOid --jq .headRefOid)
   sleep 3
   HEAD2=$(gh pr view "$PR_URL" --json headRefOid --jq .headRefOid)
   test "$HEAD1" = "$EXPECTED_HEAD" && test "$HEAD2" = "$EXPECTED_HEAD"
   ```
6. Mention in the final summary when a stale approval was intentionally avoided and the final reviewed SHA.

Pitfall: `git fetch origin pull/N/head:refs/remotes/origin/pr-N` fails with `non-fast-forward` after a force-push. Use the leading `+` refspec for review worktrees; it is safe because the local ref is only a disposable PR review ref.
