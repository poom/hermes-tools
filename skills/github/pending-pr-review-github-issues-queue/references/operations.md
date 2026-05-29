# Operations

All commands run from the skill directory unless an installed `${HERMES_HOME}`
path is shown. All live GitHub mutations require `--apply`.

## Coordinator

Dry-run discovery and reconciliation:

```bash
python3 scripts/coordinator.py \
  --queue-repo poom/hermes-pr-review-queue \
  --reviewer poom \
  --create-repo \
  --ensure-labels
```

Apply live queue mutations:

```bash
python3 scripts/coordinator.py \
  --queue-repo poom/hermes-pr-review-queue \
  --reviewer poom \
  --create-repo \
  --ensure-labels \
  --apply
```

Coordinator responsibilities:

- run `pending-pr-review/scripts/list_pending_prs.sh --stats-json`;
- optionally create the private queue repo when `--create-repo --apply` is used;
- fetch each PR's live head SHA;
- skip closed, merged, draft, stale, or already-current-head-reviewed PRs;
- create one queue issue per current `repo#number@head_sha`;
- leave exact open duplicates alone;
- do not recreate closed `hermes:done` or skipped items for the same key;
- supersede older open issues for the same PR with different `head_sha`;
- reconcile obsolete open queue issues.

## Enqueue One PR URL

When Poom provides only a PR URL or `OWNER/REPO#NUMBER`, post it to the queue
board without waiting for GitHub review-request discovery:

```bash
python3 scripts/enqueue_pr.py \
  'https://github.com/EWA-Services/user-iam/pull/201' \
  --queue-repo poom/hermes-pr-review-queue \
  --requested-by manual
```

Apply live queue mutation:

```bash
python3 scripts/enqueue_pr.py \
  'https://github.com/EWA-Services/user-iam/pull/201' \
  --queue-repo poom/hermes-pr-review-queue \
  --requested-by manual \
  --ensure-labels \
  --apply
```

The script fetches the live PR head, checks current-head Poom formal reviews,
dedupes by `queue_key`, updates an existing current-head issue instead of
duplicating it, and supersedes older open queue issues for the same PR.

## Worker

Dry-run the next claim:

```bash
python3 scripts/worker.py run \
  --queue-repo poom/hermes-pr-review-queue \
  --worker-name mac
```

Claim one issue and schedule a one-shot Hermes review job:

```bash
python3 scripts/worker.py run \
  --queue-repo poom/hermes-pr-review-queue \
  --worker-name mac \
  --schedule-hermes \
  --apply
```

Claim one issue and print the handoff prompt:

```bash
python3 scripts/worker.py run \
  --queue-repo poom/hermes-pr-review-queue \
  --worker-name mac \
  --claim-only \
  --apply
```

Worker responsibilities:

- process at most one issue per run;
- acquire a local overlap lock under `${HERMES_HOME:-$HOME/.hermes}/run`;
- post a claim comment with a 90 minute lease;
- continue only if this worker has the earliest non-expired claim;
- add `hermes:claimed` and `worker:<name>` labels after winning;
- run live PR state and current-head duplicate-review gates before review work;
- hand off actual PR review to `pr-review-guardrails`;
- record a result comment and close/update labels after verified review posting.

## Heartbeat

Long reviews should extend the lease:

```bash
python3 scripts/worker.py heartbeat \
  --queue-repo poom/hermes-pr-review-queue \
  --issue-number 123 \
  --worker-name mac \
  --lease-id mac-20260528T175228Z-a1b2c3 \
  --queue-key EWA-Services/finn-web-app#4974@abc123456789 \
  --apply
```

## Record Result

After the review is posted and verified, close the queue issue:

```bash
python3 scripts/worker.py record-result \
  --queue-repo poom/hermes-pr-review-queue \
  --issue-number 123 \
  --worker-name mac \
  --lease-id mac-20260528T175228Z-a1b2c3 \
  --queue-key EWA-Services/finn-web-app#4974@abc123456789 \
  --result approved \
  --pr-review-id 1234567890 \
  --review-state APPROVED \
  --commit-id abc123456789 \
  --summary "Approved current head after guardrail review" \
  --apply
```

Valid result values:

- `approved`
- `changes-requested`
- `commented`
- `skipped`
- `stale`
- `superseded`
- `already-reviewed`
- `closed`
- `draft`
- `failed`

## Stale Sweep

Requeue claimed issues whose winning lease/heartbeat is expired:

```bash
python3 scripts/worker.py sweep-stale \
  --queue-repo poom/hermes-pr-review-queue \
  --apply
```

The stale sweep does not steal non-expired claims.

## Cron Commands

Coordinator, one machine only:

```bash
python3 ${HERMES_HOME:-$HOME/.hermes}/skills/github/pending-pr-review-github-issues-queue/scripts/coordinator.py \
  --queue-repo poom/hermes-pr-review-queue \
  --reviewer poom \
  --create-repo \
  --ensure-labels \
  --apply
```

Worker, every participating machine:

```bash
python3 ${HERMES_HOME:-$HOME/.hermes}/skills/github/pending-pr-review-github-issues-queue/scripts/worker.py run \
  --queue-repo poom/hermes-pr-review-queue \
  --worker-name "$(hostname -s)" \
  --schedule-hermes \
  --apply
```

## Offline Tests

Run from this skill directory:

```bash
python3 -B scripts/test_queue_common.py
python3 -B scripts/test_coordinator.py
python3 -B scripts/test_enqueue_pr.py
python3 -B scripts/test_worker.py
python3 -m py_compile scripts/queue_common.py scripts/coordinator.py scripts/enqueue_pr.py scripts/worker.py
```
