# Stacked / stale PRs with noisy GitHub diffs

Use this when a PR is part of a stack or has `mergeStateStatus=DIRTY`/`BEHIND`, and the normal `base...HEAD` diff includes many unrelated files from adjacent stack phases or older base history.

## Pattern

A scheduled pending-review run hit this on `EWA-Services/Tools` atlas-scout PRs: the live PR was code-reviewable on its current head, but GitHub reported a dirty/stale merge state and local `origin/main...HEAD` / `origin/main..HEAD` diffs were noisy because the branch carried stacked-base history. Prior review threads and the current head implementation were more reliable than treating the entire noisy diff as PR-owned scope.

## Review approach

1. Refresh live PR state first: head SHA, `baseRefName`, `reviewDecision`, `mergeStateStatus`, checks, comments, reviews, and review threads.
2. If the branch is stacked/stale and the diff is noisy, do **not** approve from the raw diff alone and do **not** request changes just because unrelated adjacent-stack files appear.
3. Build a scope ledger from:
   - PR title/body and linked spec/ticket.
   - Changed files that are clearly owned by this phase.
   - Prior inline threads and author replies.
   - Current implementation at `HEAD` for the files implicated by those threads.
4. Revalidate each old blocker against current code and tests. Classify author replies normally: fixed/clear + credible, clear but unimplemented, unclear, or disagreement needing evidence check.
5. Run the narrow package/repo tests that correspond to the PR-owned scope, plus `git diff --check`. If the full diff is noisy, state that the approval is based on current-head scoped inspection rather than treating every noisy diff file as owned by the PR.
6. Treat `DIRTY`, `BEHIND`, stale policy-bot rows, and stacked-base conflicts as process/merge-readiness notes unless the current PR-owned code itself regresses the shared contract.
7. If approving, make the formal review explicit that the approval applies to the sampled current head and that a post-rebase/update re-check is needed if the diff changes materially.

## Wording for approval bodies

> This approval applies to current head `<sha>`. GitHub currently reports the branch as stale/dirty against `main`; please update/rebase and re-green process gates before merge. If the update materially changes the PR-owned diff, re-check before merging.

## Pitfalls

- Do not let noisy stacked diffs hide real shared-contract regressions: inspect the shared files implicated by old blockers (for example shared runner/sheets helpers) at current `HEAD`.
- Do not post duplicate reviews if Poom already has a current-head approval; classify the PR as process/merge-blocked instead.
- Do not report the raw pending queue as clear when only process-blocked, current-head-approved PRs remain.
