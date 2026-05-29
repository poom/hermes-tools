# Failed finn-ai-coder review checks: separate substantive verdict from wrapper failure

Use this when a PR has a failing `finn-ai-coder / review` or `code-review / Finish finn-ai-coder review check` row.

## Pattern

The workflow/check can fail for two different classes of reasons:

1. **Wrapper/comment-posting/process failure** after the direct CLI reviewer already produced an approve-level body.
2. **Substantive review failure** where the bot's formal review body and metadata report `REQUEST_CHANGES` with a concrete code finding.

Do not classify the red check as process noise until you inspect the bot review body and/or failed workflow log metadata.

## Evidence to collect

- `gh pr checks --json name,state,bucket,link,workflow`
- `gh api repos/OWNER/REPO/pulls/PR/reviews --paginate`
- `gh run view RUN_ID --log-failed --repo OWNER/REPO` for the failed review workflow
- Any top-level PR comment from the direct CLI review.

## Classification

Treat as **process noise** when the log/review evidence says the substantive Codex/direct-CLI verdict was approve-level/no actionable findings and the failure is only that the wrapper did not post/finish the expected top-level comment or refresh row.

Treat as a **real current-head blocker** when the bot review or metadata says `REQUEST_CHANGES` and names a concrete finding. Example: `verdict_reason: API-facing BullMQ operations parse a timeout config but still wait without applying it`. In that case, read the inline comment and verify the code before either carrying it forward or downgrading it.

## Review body wording

When it is process noise, say the check failure is a workflow/comment-posting artifact and cite the approve-level substantive verdict.

When it is substantive, do not hide it under “metadata gate noise.” Include the finding in the guardrail review synthesis, de-duplicate against the bot's inline comment, and either request changes or explain with evidence why the finding is stale/incorrect on the current head.
