# Atlas Scout Reports source-migration PR case

Use this reference for `atlas-scout-reports` PRs that migrate deterministic report source from a skill/JAI-style layout into the Tools repo without yet rewiring production cron wrappers or live delivery.

Originating case: `EWA-Services/Tools#132` (`feat(atlas-scout-reports): migrate 4 deterministic TA reports from jai/skills [ENG-951]`). This was a parent-delegated/report-only review: no GitHub comments/reviews, no Discord/Telegram/chat messages, no channel creation.

## Review shape

1. Confirm scope from PR body and linked ticket.
   - For Tools #132, ENG-951 described follow-up cron/wrapper path rewiring and TA SLA Snapshot chaining; the PR itself was only a source-code migration for side-by-side validation.
   - Do not demand production wrapper changes when the PR explicitly defers live cutover.
2. Build a current-head evidence packet:
   - `gh pr view ... --json headRefOid,baseRefOid,mergeStateStatus,reviewDecision,title,url`
   - `gh pr checks ... --watch=false || true`
   - Pull formal reviews via `gh api repos/OWNER/REPO/pulls/N/reviews --paginate`.
   - Query review threads with GraphQL when needed and record total/unresolved counts.
3. Check migrated report runtime viability without live delivery:
   - Run `--help` for each migrated runner to exercise imports/arg parsing.
   - Run `python3 -m compileall` on the migrated report tree and changed tests.
   - Run ruff check/format on the migrated report tree and changed tests.
   - Run the explicit changed-test subset rather than a broad glob that can pull in unrelated stale tests.
4. Validate delivery safety:
   - Delivery must be gated behind explicit `--deliver` or equivalent; default should render/output only.
   - If Chat delivery exists, verify pre-send/deterministic validation runs before sending and blocks invalid artifacts.
   - Check `gog chat messages send` argv shape, account/thread/text/json handling, and that candidate Chat body artifacts are recorded before send.
5. Scan for sensitive data:
   - Search new/changed files for token/password/private-key/API-key patterns, but report only actual introduced literals. Env-var names alone are not secret leakage.
6. Classify CI failures carefully:
   - In Tools #132, current remote `Run pytest` failed during collection on stale unrelated forbidden-words tests with `ModuleNotFoundError: job_posting_forbidden_words`; the changed atlas-scout subset passed locally.
   - Treat unrelated stale collection failures as merge/process blockers, not current-diff code blockers. Preserve the distinction in the final verdict.
7. Check adjacent non-additive test edits.
   - In Tools #132, `tests/test_claude_bq_mcp_bigquery_tools.py` was correctly updated to monkeypatch `bigquery_client.bigquery_request` after the client split and to accept extra kwargs such as `audit_context` in `dry_run_job` stubs.
8. For later re-approval deltas that package an adjacent Atlas Scout report into `atlas-scout-reports/src`, validate both the repo-level import harness and package-level install/runtime.
   - Concrete Tools #132 follow-up: current head `3a20fa21478ce09756a5dc7810816c8e8571eea5` only changed forbidden-words packaging/tests after prior approval. The safe re-review inspected `bb8b3ae..HEAD`, verified `poom` lacked a pulls-review `commit_id` matching current head, ran focused forbidden-words tests plus the previously approved atlas-scout subset, then additionally ran package-local `uv run --python 3.11 --extra test atlas-scout-reports --version` and `uv run --python 3.11 --extra test python -m pytest tests -q` from `atlas-scout-reports/`.
   - When eager imports are removed from `atlas_scout_reports.reports.__init__` but `__all__` remains, do not assume star-import breaks; verify directly with `PYTHONPATH=atlas-scout-reports/src python3 -c 'from atlas_scout_reports.reports import *'` (or equivalent) before carrying that as a caveat.
   - For Unicode matcher fixes, check the intent separately: Latin accent-insensitive matching should still work, while Thai/non-Latin combining marks should not be stripped into a different matching surface. Focused tests over English glosses, Thai allowed/forbidden overrides, text normalization, and full top-level tests are sufficient if remote CI is green.

## Useful commands from the case

```bash
git diff --check origin/main...HEAD

uvx ruff check atlas-scout-reports/ tests/test_atlas_scout_*.py tests/test_claude_bq_mcp_bigquery_tools.py
uvx ruff format --check atlas-scout-reports/ tests/test_atlas_scout_*.py tests/test_claude_bq_mcp_bigquery_tools.py

uvx --with pytest --with requests pytest \
  tests/test_atlas_scout_greenhouse_retry.py \
  tests/test_atlas_scout_job_posting_intro_fixtures.py \
  tests/test_atlas_scout_job_posting_intro_render.py \
  tests/test_atlas_scout_job_posting_intro_run.py \
  tests/test_atlas_scout_report_chat_body_validation.py \
  tests/test_atlas_scout_report_validation.py \
  tests/test_atlas_scout_ta_refresh_banner_render.py \
  tests/test_atlas_scout_ta_refresh_render.py \
  tests/test_atlas_scout_ta_refresh_run.py \
  tests/test_atlas_scout_ta_sla_snapshot_render.py \
  tests/test_atlas_scout_ta_sla_snapshot_run.py \
  tests/test_atlas_scout_weekly_sourcing_chat_render.py \
  tests/test_atlas_scout_weekly_sourcing_render.py \
  tests/test_atlas_scout_weekly_sourcing_run.py \
  tests/test_claude_bq_mcp_bigquery_tools.py -q

python3 -m compileall -q atlas-scout-reports tests/test_atlas_scout_*.py tests/test_claude_bq_mcp_bigquery_tools.py

python3 atlas-scout-reports/job_posting_intro/report_job_posting_intro_run.py --help >/tmp/job-help.txt
python3 atlas-scout-reports/ta_refresh/report_ta_refresh_run.py --help >/tmp/refresh-help.txt
python3 atlas-scout-reports/ta_sla_snapshot/report_ta_sla_snapshot_run.py --help >/tmp/sla-help.txt
python3 atlas-scout-reports/weekly_sourcing/report_weekly_sourcing_run.py --help >/tmp/weekly-help.txt
```

## Verdict pattern

Approve-level code verdict is appropriate when:

- The PR is scoped to source migration and leaves live production wrappers untouched by design.
- Changed tests, compile, lint/format, whitespace, and runner import/help checks pass.
- Delivery defaults remain non-live and any live send path is explicitly gated plus pre-send validated.
- No introduced secret/PII literals are found.
- Current red CI is demonstrably unrelated/stale and called out as merge/process readiness rather than a code blocker.

Use `APPROVE` as the proposed action in parent-delegated mode, but return `github_action_performed: none` and include the complete proposed review body for the parent to post after a final head check.

## Pitfalls

- Do not trust SHAs quoted in older review bodies as proof of what commit the formal review attaches to. Use the review object's `commit_id` and the PR `headRefOid`; Tools #132 had a current-head formal approval whose body text mentioned an older SHA.
- Do not run broad globs blindly if the repository has stale tests outside the PR scope; list changed tests explicitly and then separately classify full-CI failures.
- Do not collapse merge readiness and code-review verdict. A PR can be approve-level but still `mergeStateStatus=BLOCKED` due unrelated red CI or `policy-bot` pending.
- Do not create Discord channels, send chat messages, or post GitHub reviews in parent-delegated/report-only mode, even if the normal skill defaults would post.
