# Base-refresh during PR review + stale process-gate rows

Use this case when a PR head changes during review because the author merges/rebases current `main` into the PR, and GitHub checks show stale failed process rows after a current-head approval.

## Pattern observed

In `EWA-Services/employer-email-enrichment-service#11`, the reviewed head changed from `cdb87ec` to `3f9ef06` while the final approval body was prepared. `OLD_HEAD..NEW_HEAD` showed release/version, Digger, and Terraform secret-manager files from the base branch refresh, while the live PR-owned `base...HEAD` diff still showed the same durable-state / BullMQ foundation diff.

A stale approval would have been unsafe, so the correct sequence was:

1. Abort posting when `gh pr view --json headRefOid` no longer matches the reviewed SHA.
2. Fetch the real base and force-fetch the PR ref:
   ```bash
   BASE=$(gh pr view 11 --repo OWNER/REPO --json baseRefName --jq .baseRefName)
   git fetch origin "$BASE:refs/remotes/origin/$BASE" +pull/11/head:refs/remotes/origin/pr-11
   git reset --hard refs/remotes/origin/pr-11
   ```
3. Inspect both:
   ```bash
   git diff --name-status OLD_HEAD..HEAD
   git diff --stat refs/remotes/origin/$BASE...HEAD
   ```
   Treat `OLD_HEAD..HEAD` base-refresh files as context, not automatically PR-owned blockers.
4. Re-run local validation that covers the reviewed behavior (`npm run build`, `npm test`, `npm run lint`, targeted smoke) on the new head.
5. Only then submit the formal review using the new SHA in the body.

## Additional observed variant: base refresh only changes base-side files

In `EWA-Services/Infrastructure#4342`, the head changed during review from `1886ac23` to `efd5fcac` after a base/main refresh. `OLD_HEAD..NEW_HEAD` showed a staging ACS values file from main, but the live PR-owned `main...HEAD` diff remained the same three production files. The correct action was to abort the stale post, force-fetch the PR and real base, inspect both `OLD_HEAD..HEAD` and `base...HEAD`, rerun lightweight validation (`git diff --check` and Ruby YAML parse), then post the approval on the new SHA.

Process-gate nuance from the same PR:

- `finn-ai-coder / review` and `metadata-gate / Refresh finn-ai-coder review check` may initially fail because the previous AI review metadata is for the old head; after a current-head manual approval, the metadata follow-up can refresh to pass.
- `ai-assistance-disclosure / AI Label Check` can remain a real process failure when exactly one of `ai-assisted` or `not-ai-assisted` is required. Report it as a merge/process blocker, not a code blocker.
- `policy-bot: main` can remain pending immediately after approval (`0/1 rules approved`) before updating; report the observed state instead of assuming it cleared.

## Process-gate row quirks

After approval on the current head, `gh pr checks` can still list stale failures from older workflow attempts alongside newer passing replacements. In the same PR:

- `Validate GrowthBook Link` displayed a failed row because the PR lacked a GrowthBook link or approved `no experiment` override. This was a process gate, not a code-review blocker for the durable-state diff.
- `finn-ai-coder / review` and `metadata-gate / Refresh finn-ai-coder review check` displayed failed rows from a pre-approval refresh (`failure (none)`) while a newer `metadata-gate / PR metadata gate (AI review follow-up)` passed after the manual approval.
- `policy-bot: main` changed from failed/disapproved to pass after approval, but `reviewDecision` could still read `CHANGES_REQUESTED` because of older bot requested-changes reviews.

Use both commands before summarizing readiness:

```bash
gh pr checks PR --repo OWNER/REPO --watch=false || true
gh run list --repo OWNER/REPO --branch HEAD_BRANCH --limit 15 \
  --json databaseId,name,status,conclusion,createdAt,updatedAt,headSha
```

If logs are needed:

```bash
gh run view RUN_ID --repo OWNER/REPO --log-failed || true
```

## Review wording

For approve-level code reviews with these gates, use `APPROVE` and say:

- Code: merge-ready / approved.
- Merge readiness: blocked or unstable until named process gates clear.
- For GrowthBook: exact next action is “add a GrowthBook link or an approved `no experiment` override comment.”
- For stale AI-review/check rows: say a current-head bot refresh/dismissal may be needed; do not reclassify the code verdict as `REQUEST_CHANGES` unless the current diff has a concrete blocker.
