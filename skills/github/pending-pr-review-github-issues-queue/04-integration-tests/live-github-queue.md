# Live GitHub Queue Integration Test

Use a temporary private repo or the real queue repo only after dry-run output is
verified. Do not run this against product PRs until the dummy race test passes.

## Preconditions

- `gh auth status` succeeds.
- Queue repo exists and issues are enabled.
- The queue repo is private.
- The test PR is harmless, or the worker is run in `--claim-only` mode.

## Steps

1. Ensure labels:
   ```bash
   python3 scripts/coordinator.py --queue-repo OWNER/QUEUE --create-repo --ensure-labels --apply --pending-pr-json /tmp/empty-prs.json
   ```
2. Create one dummy issue with a valid `hermes-pr-review-queue-item` block.
3. Start two workers within a few seconds:
   ```bash
   python3 scripts/worker.py run --queue-repo OWNER/QUEUE --worker-name mac --claim-only --apply
   python3 scripts/worker.py run --queue-repo OWNER/QUEUE --worker-name ubuntu --claim-only --apply
   ```
4. Inspect issue comments and labels.

## Expected Result

- Both workers may post claim comments.
- Exactly one worker computes itself as the winner.
- The losing worker exits without review work.
- The issue ends with `hermes:claimed` and exactly one `worker:<name>` label.
- No product PR review is posted during `--claim-only` testing.
