# Dummy Queue Race Smoke

This smoke test validates the claim protocol without posting a product PR
review.

## Setup

Create or choose a private queue repo:

```bash
QUEUE_REPO=OWNER/hermes-pr-review-queue-test
python3 scripts/coordinator.py --queue-repo "$QUEUE_REPO" --create-repo --ensure-labels --apply --pending-pr-json /tmp/empty-prs.json
```

Create one dummy issue with:

- label `hermes:queued`
- label `source:pending-pr-review`
- a valid `hermes-pr-review-queue-item` block
- a harmless PR URL/head SHA

## Run

Queue a harmless PR URL in dry-run mode first:

```bash
python3 scripts/enqueue_pr.py https://github.com/EWA-Services/user-iam/pull/201 --queue-repo "$QUEUE_REPO"
```

In two terminals:

```bash
python3 scripts/worker.py run --queue-repo "$QUEUE_REPO" --worker-name mac --claim-only --apply
python3 scripts/worker.py run --queue-repo "$QUEUE_REPO" --worker-name ubuntu --claim-only --apply
```

## Pass Criteria

- At most one worker prints a handoff prompt.
- The other worker prints that it lost the claim.
- The issue has append-only claim evidence for the race.
- The issue is labeled `hermes:claimed`.
- No GitHub PR review is posted.
