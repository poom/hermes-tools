# Head moved before posting / cutoff recovery

Use this when a scheduled pending-review drain completes substantial local evidence gathering for a PR, but detects that the PR branch/head moved before the formal GitHub review was posted, or the run hits a tool/runtime cutoff immediately after that detection.

## Durable pattern

1. Treat all local review evidence as stale once a different remote head is observed.
   - `gh pr view` / REST pull head may briefly disagree with `git ls-remote` during force-pushes or branch updates; when `git ls-remote origin refs/heads/<headRefName>` shows a SHA different from the local reviewed head, do **not** post the drafted verdict.
   - Record both SHAs in the local cutoff/recovery note.
2. Do not submit a formal review, even if the stale evidence was approve-level.
3. Do not send a final per-PR result that says approved/requested changes. If a PR channel was already created, report it as **started / stale-head abort / no GitHub action** only if delivery budget remains.
4. Recovery run must re-fetch the live PR state and start from the duplicate-current-head gate again:
   - current head SHA
   - current `poom` review decision for that exact `commit_id`
   - current diff, comments/reviews/threads, checks, and process state
   - delta from the stale reviewed SHA to the live head, if useful
5. If the platform stops tool calls after the head-move detection, final local response should include:
   - completed PRs with verified review ids/messages
   - the stale PR URL/channel and stale reviewed SHA
   - the newly observed live SHA
   - `GitHub action: none / no formal review posted`
   - `final live queue clearance was not re-verified`

## Recommended wording

```text
Started but not completed:
- <repo> #<num> — head moved before posting.
  Reviewed-local head: <old_sha>
  Newly observed live head: <new_sha>
  GitHub action: none / no formal review posted.
  Required recovery: re-fetch current head, re-run duplicate-review gate, revalidate the live diff, then post/report normally.
```

## Why this matters

In a sequential rmux drain, it is better to leave a PR pending than to attach an approval/request-changes review to stale evidence. A branch can move after local validation but before the final GitHub review, and GraphQL/`gh pr view` can be unavailable at the same time. A raw `git ls-remote` check is a cheap extra guard, but a mismatch is an abort signal, not a reason to keep using the old body.
