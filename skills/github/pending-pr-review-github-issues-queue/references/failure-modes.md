# Failure Modes

## Worker Loses Claim Race

Two workers can post claim comments at nearly the same time. Both workers must
refetch comments and compute the same winner from the append-only claim history.
The loser exits successfully without reviewing.

## Worker Dies Mid-Review

State:

- issue has `hermes:claimed`;
- winning claim or heartbeat expires;
- no result comment exists.

Recovery:

- `scripts/worker.py sweep-stale --apply` can requeue expired claims;
- next worker still performs live PR state and duplicate-review gates before
  doing review work.

## Worker Posts Review But Crashes Before Closing Issue

Recovery:

- worker preflight or coordinator reconciliation checks pulls reviews API;
- if Poom already has a current-head formal decision, mark skipped/done and
  close the queue issue;
- never post another review for the same current head.

## PR Head Moves While Queued Or Claimed

Required behavior:

- worker live-head preflight detects the mismatch;
- worker does not review or post saved/stale output;
- queue issue is marked `hermes:stale` and `hermes:superseded`, then closed;
- coordinator or `scripts/enqueue_pr.py` creates the current-head issue.

## Duplicate Current-Head Issue Exists

`scripts/enqueue_pr.py` and `scripts/coordinator.py` search exact `queue_key`.
If an open current-head issue already exists, update/comment that issue instead
of creating a duplicate.

## Old Same-PR Issue Exists

If an older open same-PR issue has a different head SHA, create or update the
fresh current-head issue and supersede the old one.

## Closed Done Issue Exists

If the exact same current-head issue is already closed as `hermes:done` or
`hermes:skipped`, do not recreate it by default. `scripts/enqueue_pr.py` accepts
`--force-rereview` for explicit re-review requests.

## Outside Allowed Owner Scope

When `scripts/enqueue_pr.py --allowed-owner` is used and a PR is outside the
allowed owners, create a confirmation issue instead of a queued worker task. The
issue gets `needs:poom-confirmation` and no `hermes:queued` label.

## GitHub Auth, Rate Limit, Or API Failure

Do not mutate product PRs. Emit a concise error and retry on the next scheduled
coordinator/worker run after auth or rate limits recover.
