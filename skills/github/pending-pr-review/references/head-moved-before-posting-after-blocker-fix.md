# Head moved before posting after a blocker fix

Use this when a scheduled pending-review run has already gathered evidence or drafted a `REQUEST_CHANGES`/`APPROVE` body, but the final pre-submit head check shows the PR head moved.

Concrete pattern from a user-iam IAM deny-policy review:

1. **Abort the stale body immediately.** Do not post the old verdict, even if the blocker looked solid on the previous head.
2. **Refresh live state on the new head:** `gh pr view` head/reviewDecision/merge state, pulls reviews, issue comments, review comments/threads, checks, and `base...HEAD` diff.
3. **Compare `OLD..NEW` as well as `base...HEAD`.** This distinguishes a direct blocker fix from unrelated rebases or base refreshes.
4. **Revalidate the old finding against the new diff.** If the new head directly scopes/narrows/removes the risky change, mark the old finding resolved/stale instead of repeating it.
5. **Run a compact current-head reviewer refresh when time/budget allows.** A short direct-Claude evidence-only prompt over the new diff + old blocker is enough for many one-line fix cases; do not rely on old-head reviewer output as current evidence.
6. **Post only after the duplicate-current-head gate.** Re-query pulls reviews for `user.login == "poom"`, `commit_id == headRefOid`, and `state in (APPROVED, CHANGES_REQUESTED)` immediately before submitting.
7. **Report the old-head lane accurately.** Say the stale body was aborted and no GitHub review was posted from it; then report the current-head action/review id.

If the new head cannot be revalidated within the remaining budget, do not post the saved body. Report the PR as unfinished/still pending with old and new SHAs and require a recovery run to refresh evidence and duplicate-gate before posting.
