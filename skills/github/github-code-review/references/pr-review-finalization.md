# PR review finalization notes

These notes cover recurring cleanup/communication issues after a PR review has been run locally and/or posted to GitHub.

## Close the loop in chat

After posting or confirming a formal review, send a concise final response in the originating chat/thread. Include:
- decision: approved/commented/changes requested
- whether the GitHub review was posted or already present at the current head
- code blockers vs process/check blockers
- local verification commands and pass/fail summary
- any runtime/config caveats needed before rollout

Do not end with only the GitHub side effect; the user asked in chat and needs the chat closure too.

## Verify head and posted review

Before posting, re-check the PR head SHA and use that SHA in the review if possible. After posting, confirm via the Pull Request Reviews API that the review exists at the expected commit. If a current-head approval already exists, avoid duplicate reviews and report that it was already posted/confirmed.

## Keep local install artifacts out of the review

Package-manager installs can modify lockfiles through install hooks, forced resolutions, or platform/node-version differences. Before finalizing:
- run `git status --short`
- inspect unexpected lockfile/config diffs
- revert local-only install artifacts
- report the verified source state, not transient local dependency churn

## Separate code findings from process gates

When checks fail due to policy evaluation, metadata refresh, stale AI-review workflow execution, or other automation/process failures, state that separately from the code verdict. Do not convert a process gate into a code blocker unless there is a concrete failing test, diff issue, security concern, or functional defect.

## Formatter mismatch handling

If local formatting/prettier check disagrees with remote pre-commit on the same head:
- identify the exact file/diff
- call it style-only if it does not affect generated artifacts or protected checks
- mention it as non-blocking author follow-up
- do not block an otherwise correct implementation solely on local formatter drift unless branch protection requires it
