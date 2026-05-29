# Queue Protocol

## Queue Repo

Default queue repo:

```text
poom/hermes-pr-review-queue
```

The queue repo should be private. If the queue repo is not available, use the
scripts in dry-run mode only.

## Labels

Core state labels:

- `hermes:queued`
- `hermes:claimed`
- `hermes:done`
- `hermes:failed`
- `hermes:skipped`
- `hermes:stale`
- `hermes:superseded`

Source and result labels:

- `source:pending-pr-review`
- `source:chat-request`
- `origin:manual`
- `origin:discord`
- `origin:telegram`
- `priority:normal`
- `priority:high`
- `needs:poom-confirmation`
- `result:approved`
- `result:changes-requested`
- `result:commented`
- `result:skipped`

## Queue Item Schema

One issue represents one PR at one specific head SHA.

Queue key:

```text
<owner>/<repo>#<pr_number>@<head_sha>
```

Issue body marker:

````markdown
<!-- hermes-pr-review-queue-item -->
```yaml
schema_version: 1
queue_key: EWA-Services/finn-web-app#4974@abc123456789
repo: EWA-Services/finn-web-app
pr_number: 4974
pr_url: https://github.com/EWA-Services/finn-web-app/pull/4974
head_sha: abc123456789
reviewer: poom
source: pending-pr-review
created_by: hermes-pr-review-discovery
created_at: 2026-05-28T17:52:28Z
```
````

## Manual Request Block

`scripts/enqueue_pr.py` adds a minimal request block when a PR URL is queued
manually or from chat:

````markdown
<!-- hermes-pr-review-chat-request -->
```yaml
schema_version: 1
requested_by: manual
requested_at: 2026-05-28T17:52:28Z
source_platform: manual
source_message_url: ""
delivery_target: ""
request_text: https://github.com/EWA-Services/user-iam/pull/201
priority: normal
```
````

## Claim Protocol

GitHub issue labels are state hints. The ownership source of truth is the
comment history.

Claim comments:

````markdown
<!-- hermes-pr-review-claim -->
```yaml
kind: claim
schema_version: 1
worker: mac
lease_id: mac-20260528T175228Z-a1b2c3
claimed_at: 2026-05-28T17:52:28Z
expires_at: 2026-05-28T19:22:28Z
queue_key: EWA-Services/finn-web-app#4974@abc123456789
```
````

Winner selection:

1. Parse all valid claim comments for the queue key.
2. Apply latest valid heartbeat expiry for each lease.
3. Discard expired leases.
4. Winner is earliest `claimed_at`.
5. Tie-breaker is the lowest GitHub comment id.

If two workers race, both should compute the same winner after refetching
comments. The loser exits without reviewing.

## Mandatory Review Gates

Before expensive review work and again immediately before any formal GitHub
review post:

```bash
gh pr view "$PR_NUMBER" --repo "$PR_REPO" \
  --json headRefOid,state,isDraft,reviewRequests,reviewDecision,mergeStateStatus,url,title

gh api "repos/$PR_REPO/pulls/$PR_NUMBER/reviews" --paginate
```

Abort or mark skipped when:

- PR is closed or merged;
- PR is draft;
- live `headRefOid` differs from queue issue `head_sha`;
- Poom already has a current-head formal `APPROVED` or `CHANGES_REQUESTED`
  review in the pulls reviews API.

Do not use aggregate `reviewDecision == APPROVED` as proof that Poom has
reviewed the current head. Filter formal reviews by:

```text
user.login == "poom"
commit_id == current headRefOid
state in {"APPROVED", "CHANGES_REQUESTED"}
```

## Stale Head Behavior

If `scripts/enqueue_pr.py` sees older open issues for the same PR, it creates or
updates the fresh current-head issue and marks old ones `hermes:stale` and
`hermes:superseded` before closing them as not planned.

If `scripts/worker.py` picks up an old queue issue after the PR head moved, it
must not review or post. It records a `stale` result, removes queued/claimed
labels, adds stale/superseded labels, and closes the issue as not planned.
