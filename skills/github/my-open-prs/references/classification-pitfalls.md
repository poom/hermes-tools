# My Open PRs Classification Pitfalls

## `mergeStateStatus=BLOCKED` is not automatically author feedback

GitHub can report `mergeStateStatus: BLOCKED` for several reasons. Do not classify it as `Needs My Feedback` unless there is specific author-action evidence such as:

- `reviewDecision: CHANGES_REQUESTED` or latest review state `CHANGES_REQUESTED`
- failing checks (`FAILURE`, `ERROR`, `ACTION_REQUIRED`, etc.)
- merge conflicts (`DIRTY`)
- branch behind base (`BEHIND`)

If the PR is already approved and `BLOCKED` is paired with a pending `policy-bot` status or an outstanding `reviewRequests` entry, classify it as `Waiting on Review` instead. Example observed on FINN-Web-App #4975:

- `reviewDecision: APPROVED`
- `mergeStateStatus: BLOCKED`
- `reviewRequests`: `@faiq-ewa`
- `policy-bot: main`: pending, `0/1 rules approved`

Correct summary: `Waiting on Review — waiting for review from @faiq-ewa` (or required policy approval if no reviewer is named), not `Needs My Feedback`.

## Verification commands

Use live GitHub evidence before explaining a surprising bucket:

```bash
gh pr view <number> --repo <owner>/<repo> --json number,title,url,author,reviewDecision,reviewRequests,reviews,comments,commits,statusCheckRollup,mergeStateStatus,isDraft,updatedAt
gh pr checks <number> --repo <owner>/<repo> --watch=false
python3 scripts/my_open_prs.py --query 'is:open is:pr author:@me archived:false org:ewa-services draft:false repo:<owner>/<repo> <number>' --json
```

After changing classifier behavior, run:

```bash
python3 scripts/test_my_open_prs.py
```
