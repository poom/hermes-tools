# Superseded identical Terraform PR plan evidence

Use this when a Terraform/IAM PR is recreated under a new branch/author/ticket and the current PR's Digger plan is blocked or locked, but a superseded PR carried the same Terraform patch and already produced plan evidence.

## Approval posture

Prior plan evidence can support a code/content approval only when you prove the current PR-owned diff is identical to the planned superseded PR and the plan evidence is still applicable. It does **not** remove the current PR's process requirement to run its own Digger plan/apply before merge.

## Required checks

1. Refresh the current PR: head SHA, base, diff, comments, review threads, checks, and current-head `poom` review state.
2. Fetch the superseded PR head and compare the PR-owned diff against the current PR-owned diff:
   - Prefer `git diff origin/<base>...refs/remotes/origin/pr-old` and `git diff origin/<base>...HEAD`.
   - Record a byte/sha256 match of the patch text, or explicitly describe any delta and revalidate it.
3. Read the superseded PR's Digger plan comments/checks, not just its review body. Confirm the affected projects/resources and plan counts.
4. Verify the current ticket/PR body intentionally scopes the recreated PR the same way as the superseded PR and corrects any metadata/ticket ownership issue.
5. If the current PR's Digger is locked or blocked, classify that as a process/merge-readiness gate, not a code blocker, **only** when the identical prior plan showed the intended safe actions and no destructive/unrelated drift.
6. In the approval body, say the approval is code/content-scoped and require a fresh current-PR Digger plan/apply before merge.

## Example wording

```text
The current PR-owned diff is byte-identical to superseded PR #N's planned diff. PR #N's Digger plans showed only the intended in-place updates for <projects> with 0 creates and 0 destroys. I am approving the code/content on the current head, but the recreated PR still needs its own Digger plan/apply after the lock/process gates clear.
```

## Pitfalls

- Do not approve from old plan evidence if the current base diff differs, even if the file edits look similar.
- Do not treat a locked/missing current Digger plan as resolved; it remains a process gate before apply/merge.
- Do not rely on old review text alone. Pull the old plan comments/checks or action logs when possible.
- If the superseded PR was planned against a materially older base and current `base...HEAD` includes unrelated drift, re-run or require a fresh plan instead of transferring the old evidence.
