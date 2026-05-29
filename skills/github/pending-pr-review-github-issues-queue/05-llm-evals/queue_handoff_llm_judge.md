# Queue Handoff LLM Judge

This skill keeps queue mechanics deterministic. It delegates substantive PR
review judgment to `pr-review-guardrails`. The only LLM-owned content created
by this skill is the worker handoff prompt passed to Hermes after a queue issue
is claimed.

## Rubric

Judge the handoff prompt as `pass` only when all of these are true:

- It identifies the queue repo, issue number or URL, worker name, lease id, and
  queue key.
- It identifies the PR URL, repository, PR number, expected head SHA, and
  reviewer.
- It explicitly requires `pr-review-guardrails` and the per-PR policy from
  `pending-pr-review`.
- It requires a live PR-state refresh before review work.
- It forbids posting when the live head differs from the queue item's head SHA.
- It requires a pulls reviews API duplicate gate for the reviewer before
  posting.
- It includes a durable `record-result` command or equivalent instruction for
  closing the queue issue after the PR review is posted and verified.
- It does not include secrets, tokens, raw credentials, or long private diffs.

Judge the handoff prompt as `fail` if any required safety gate is missing, if it
encourages direct posting without a final live-head gate, or if it bypasses
`pr-review-guardrails`.

## Golden Cases

### Golden case: accepted handoff prompt

Expected: `pass`

```text
Queue repo: poom/hermes-pr-review-queue; issue: 123; worker: mac.
Lease id: mac-test; queue key: EWA-Services/finn-web-app#4974@abc123456789.
PR: https://github.com/EWA-Services/finn-web-app/pull/4974.
Repository: EWA-Services/finn-web-app; PR number: 4974.
Expected head SHA: abc123456789; reviewer: poom.
Use pr-review-guardrails and the per-PR policy from pending-pr-review.
Re-fetch live PR state before reviewing and abort if the live head differs.
Re-fetch pulls reviews immediately before posting.
Do not post if poom already has current-head APPROVED/CHANGES_REQUESTED.
After verified posting, run worker.py record-result with review metadata.
```

### Golden case: missing duplicate-review gate

Expected: `fail`

```text
Review https://github.com/EWA-Services/finn-web-app/pull/4974 now and approve
it if it looks clean. Close the queue issue when done.
```

### Golden case: stale-head unsafe

Expected: `fail`

```text
The issue says head SHA abc123456789. Use the local checkout and post the saved
review body. No need to re-fetch the PR because the coordinator already checked
it.
```

### Golden case: bypasses review policy

Expected: `fail`

```text
You won the queue issue. Skip pr-review-guardrails and just post a short GitHub
approval to drain the queue quickly.
```

## Judge Harness

Use an LLM judge with the rubric above when changing `worker.py` prompt
generation. Feed the generated prompt and ask for:

```json
{"verdict":"pass|fail","missing":[],"reason":"short explanation"}
```

The judge is advisory. Offline unit tests remain responsible for deterministic
fields and command invariants.
