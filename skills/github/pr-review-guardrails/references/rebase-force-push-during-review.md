# Rebase / Force-Push During PR Review

Use when the PR head SHA changes while reviewers or local checks are running.

## Pattern observed

A PR was force-updated/rebased while dual review was in progress. `git diff OLD_HEAD..NEW_HEAD` showed many workflow file changes because the branch was rebased onto a newer base, but the live PR diff (`base...HEAD`) still contained only the two intended test files. Treat `OLD_HEAD..NEW_HEAD` as a diagnostic for what changed between commits, not as proof the PR now owns those files.

## Safe revalidation steps

1. Refresh live PR metadata and changed files:
   ```bash
   gh pr view "$PR" --repo "$REPO" --json headRefOid,baseRefName,changedFiles,title,url
   gh pr diff "$PR" --repo "$REPO" --name-only
   ```
2. Force-fetch the true base and PR head:
   ```bash
   BASE=$(gh pr view "$PR" --repo "$REPO" --json baseRefName --jq .baseRefName)
   git fetch origin "$BASE:refs/remotes/origin/$BASE" +pull/$PR/head:refs/remotes/origin/pr-$PR
   git checkout -f refs/remotes/origin/pr-$PR
   ```
3. Re-evaluate the actual PR-owned diff, not only `OLD_HEAD..NEW_HEAD`:
   ```bash
   git diff --stat refs/remotes/origin/$BASE...HEAD
   git diff refs/remotes/origin/$BASE...HEAD -- <changed-files>
   ```
4. If `OLD_HEAD..NEW_HEAD` shows unrelated files but `base...HEAD`/`gh pr diff` does not, document it as a rebase/base refresh artifact and do not expand the review scope unnecessarily.
5. Re-run cheap affected validations after checkout refresh (`git diff --check`, lint/typecheck/targeted tests as applicable).
6. Immediately before posting a formal review, double-sample the head SHA with a short delay and abort if it changed again.

## Reporting wording

Mention briefly in the final summary: "Head changed during review, so I refreshed/revalidated against the new head; the live PR-owned diff remained <scope>." This reassures the user without dumping stale reviewer details.
