# Current-head approval after a small post-approval delta

Use this when a pending-review PR has an old Poom approval on a previous head, a local review memory entry proving a full guardrail review was already completed, and the live head has only a narrow follow-up delta.

Concrete session patterns:

- EWA-Services/Tools #145 (Codex telemetry). Poom had approved head `3b61730...`, the PR force-pushed to `5e88468...` with only Grafana dashboard/read-role changes, and the pending queue returned it because no Poom approval existed on the new head.
- EWA-Services/Tools #132 (Atlas Scout Reports migration). Poom had approved `a28434d...`; the current head `e883a12...` added only a test-expectation fix in `tests/test_claude_bq_mcp_bigquery_tools.py` after a BigQuery client split. `reviewDecision` was already `APPROVED` because bot/human state was favorable, but the pulls reviews API proved Poom had no current-head approval. The safe path was to inspect `a28434d..e883a12`, run focused test/ruff validation, run compact no-tools Claude over the delta, post a full current-head `APPROVE`, and verify `commit_id == e883a12...`.
- EWA-Services/Tools #132 later advanced from parent-reviewed `bb8b3ae...` to `3a20fa2...` with a small-but-real forbidden-words packaging/import delta. The live state still had `reviewDecision=APPROVED`, but pulls reviews API again showed no `poom` current-head `commit_id`. Approval-level recovery required: inspect `bb8b3ae..HEAD`, refresh comments/threads/checks, validate focused forbidden-words tests, full top-level tests, ruff/format/compileall, package-local `uv run` version + internal pytest from `atlas-scout-reports/`, and run compact no-tools Claude. If a reviewer flags `__all__` after eager import removal, verify star import directly before reporting it as a caveat.

## Recovery workflow

1. Refresh live PR state and formal reviews with the pulls reviews API.
   - Do not rely on `reviewDecision == APPROVED` alone; verify whether `poom` has an `APPROVED` review whose `commit_id` equals `headRefOid`.
2. Read `${HERMES_HOME:-<home>/.hermes}/pr-reviews/<repo>-<number>.md`.
   - If memory proves a full previous guardrail review but for an older head, use it as a base only after validating the old reviewed SHA.
3. Inspect the delta from previous reviewed SHA to current head:
   - `git diff --stat OLD_HEAD..HEAD`
   - `git diff --name-status OLD_HEAD..HEAD`
   - focused `git diff --unified=... OLD_HEAD..HEAD -- <changed paths>`
4. Re-read live comments/review threads for any blocker raised on the delta.
   - If the delta fixes an unresolved thread, verify current code evidence and resolve the stale thread before posting approval.
5. Run focused validation for the changed area plus cheap repository checks.
   - Example: `make -C codex-telemetry test`, `git diff --check`, JSON parse, `bash -n`, `py_compile`.
   - For test-only post-approval deltas, run the changed test file directly plus the previously-approved domain suite and linter/format checks. Example from Tools #132: `uvx --with pytest --with requests pytest tests/test_claude_bq_mcp_bigquery_tools.py -q`, `uvx --with pytest --with requests pytest tests/test_atlas_scout_*.py -q`, and `uvx ruff check ...`.
6. Run Reviewer B with a compact direct Claude CLI prompt over the delta evidence, not a full repo tool-using exploration:
   - `claude -p "$(cat /tmp/prompt.txt)" --model opus --max-turns 5 --tools ''`
   - Include PR URL/title, old reviewed SHA, current head SHA, previous findings status, current diff, check summary, and the exact question.
7. Re-check head immediately before posting.
8. Post a full `Guardrail review — Approved` body that explicitly says it reviewed the current head and the post-approval delta.
9. Verify the new review through `gh api repos/OWNER/REPO/pulls/PR/reviews --paginate` and confirm `user.login == poom`, `state == APPROVED`, and `commit_id == headRefOid`.
10. Update review memory with the new approval id and current head.

## Process-gate note

If `metadata-gate / Refresh finn-ai-coder review check` fails with text like `Refreshed finn-ai-coder / review on <head>: failure (none)` while a latest direct CLI review comment on the same head reports no actionable findings, treat it as process/metadata noise when current code evidence, tests, and human/Claude review are approve-level. Still report it as merge/process readiness, not a code blocker.
