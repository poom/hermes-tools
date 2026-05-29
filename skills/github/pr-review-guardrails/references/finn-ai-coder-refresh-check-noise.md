# finn-ai-coder refresh-check failures as process noise

## Trigger

A PR's checks include a failed `metadata-gate / Refresh finn-ai-coder review check` row, often with a companion `finn-ai-coder / review` failure, while normal code/security CI is otherwise green.

## What to inspect

Use `gh run view <run-id> --log-failed --repo <OWNER/REPO>` and look for the refresh command:

```text
python3 ewa-actions/scripts/finn_ai_coder_github_app.py refresh-check \
  --repo "$GITHUB_REPOSITORY" \
  --pr-number "$TARGET_PR_NUMBER" \
  --name "finn-ai-coder / review"
...
Refreshed finn-ai-coder / review on <head_sha>: failure (none)
finn-ai-coder review check is failure for the current PR diff.
```

This means the metadata workflow mirrored the AI-review/check verdict to a check run; it is not itself evidence of a product-code test failure.

## Review handling

- Treat the row as process/metadata state unless the underlying `finn-ai-coder / review` body contains a concrete current-head code blocker.
- If there is a newer replacement/follow-up AI-review check or formal review showing approve on the current head, prefer the current-head signal and call the failed refresh row stale/process noise.
- Do not approve blindly: still inspect the AI-review body/comments, current head, changed code, and relevant tests.
- In the review body, separate this from code readiness: e.g. `Non-blocking/process note: an older metadata refresh row is failed because it mirrored finn-ai-coder failure; code/security checks and current review evidence are approve-level.`

## Pitfall

`gh pr checks` may exit non-zero because of this failed row. Capture output with `|| true` before parsing so the review workflow does not abort before you inspect the substantive checks.
