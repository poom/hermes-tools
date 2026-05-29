---
name: pending-pr-review-github-issues-queue
description: Use when setting up or operating Poom's distributed pending GitHub PR review queue via private GitHub Issues, queueing a single PR URL onto the board, or running coordinator/worker jobs that claim one issue at a time before handing off to pr-review-guardrails.
version: 1.0.0
license: MIT
required-skills: [pending-pr-review, pr-review-guardrails]
required-binaries: [gh, python3, hermes]
required-env: []
required-mcps: []
metadata: github-pr-review-distributed-queue
---

# Pending PR Review GitHub Issues Queue

## Workflow

Use this skill to operate the shared GitHub Issues board for Poom's pending PR
reviews. The board lets one coordinator and multiple named workers process PR
reviews without duplicate reviews or shared SQLite/SMB state.

Core architecture:

```text
coordinator/enqueue_pr.py -> GitHub Issues queue -> worker.py -> pr-review-guardrails
```

Default queue repo:

```text
poom/hermes-pr-review-queue
```

Override with `HERMES_PR_REVIEW_QUEUE_REPO=OWNER/REPO` or `--queue-repo`.

## Use Cases

- Mirror live `pending-pr-review` discovery into the board with
  `scripts/coordinator.py`.
- Queue a single PR URL or `OWNER/REPO#NUMBER` onto the board with
  `scripts/enqueue_pr.py`.
- Let one machine claim and process one board issue with `scripts/worker.py`.
- Use `scripts/queue_common.py` only as shared deterministic library code.

## Rules

- Queue key is always `<owner>/<repo>#<pr_number>@<head_sha>`.
- The head SHA is part of identity. Current-head work gets a fresh issue; old
  open same-PR issues are closed as stale/superseded.
- Board mutation scripts default to dry-run. Use `--apply` only after the
  proposed action looks right.
- Workers process at most one issue per run and must win the claim-comment
  lease before review work.
- Workers must fetch live PR state before reviewing and again before posting.
- Workers must not post when the live head differs from the queue issue head.
- Workers must not post when Poom already has a current-head APPROVED or
  CHANGES_REQUESTED formal review.
- Do not put secrets, tokens, private raw prompts, customer data, or long
  sensitive diffs into queue issues.

## Quick Commands

Dry-run one PR URL onto the board:

```bash
python3 scripts/enqueue_pr.py 'https://github.com/EWA-Services/user-iam/pull/201'
```

Run the coordinator dry-run:

```bash
python3 scripts/coordinator.py --queue-repo poom/hermes-pr-review-queue --ensure-labels
```

Run one worker dry-run:

```bash
python3 scripts/worker.py run --queue-repo poom/hermes-pr-review-queue --worker-name mac
```

## References

- [Queue protocol](references/queue-protocol.md) - issue schema, labels, claim
  comments, stale-head behavior, and duplicate-review gates.
- [Operations](references/operations.md) - coordinator, enqueue, worker,
  heartbeat, result, stale sweep, cron, and offline test commands.
- [Failure modes](references/failure-modes.md) - recovery behavior for races,
  moved heads, expired leases, crashes, and auth/rate-limit failures.

## Failure Behavior

If the board state is ambiguous, prefer no PR review post over a stale or
duplicate post. Comment/label/close the queue issue when safe, or leave it open
with a concise error for the next coordinator/worker run.
