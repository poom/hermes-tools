# GitHub review verification quirks

## `gh pr view --json latestReviews` may not prove a new review posted

Observed during Account-Creation-Flow #585: after `gh pr review --approve --body-file ...` exited successfully, `gh pr view --json latestReviews,reviewDecision` still showed older reviews and `reviewDecision: CHANGES_REQUESTED` because an earlier human disapproval/policy-bot gate remained active. The newly submitted approval was present in the underlying pulls reviews API.

Use this verification command after posting a formal review:

```bash
gh api repos/OWNER/REPO/pulls/PR_NUMBER/reviews --paginate \
  --jq '[.[] | {id,user:.user.login,state,submitted_at,commit_id,body:(.body[0:80])}] | .[-8:]'
```

Interpretation:
- A successful review post should appear with the current head `commit_id`, expected `state` (`APPROVED`, `CHANGES_REQUESTED`, or `COMMENTED`), and the reviewer login.
- For current-head verification, the pulls reviews API `commit_id` is authoritative; do not rely on `latestReviews` or on SHA strings quoted inside the review body. A review body can mention an older SHA when it was reconstructed/reused, while GitHub correctly records the submitted review's `commit_id` as the current head.
- `reviewDecision` can remain `CHANGES_REQUESTED` even after your approval if another reviewer has an unresolved changes-requested review or policy-bot still blocks.
- In the chat summary, distinguish "GitHub action: approved" from "Merge readiness: approved but blocked by existing process/human gates".
