# PR velocity Chat/config review case

Use this reference for PRs that standardize engineering-throughput / PR-velocity Chat reports, especially when the report combines GitHub PR counts, AI-assistance metadata, Supabase cached records, and Sonar quality signals.

## Review focus

- **Aggregate-only output**: Chat/report output should show org/team-level aggregate trends and contextual signals, not per-user/per-team productivity rankings unless explicitly approved by policy/product. Look for roster rows, user/team labels, or rank-like formatting in renderers.
- **Disclaimer**: Throughput/AI signals should be framed as context signals, not individual productivity ratings.
- **Config defaults vs explicit flags/env**: Verify config loading honors explicit CLI flags and environment choices. A committed default such as `storage_backend: supabase` should not override an explicit runtime `STORAGE_BACKEND`/flag unexpectedly.
- **Scan windows**: Chat trend windows often need trailing 4/12-week context even if the current report window is shorter. Check that fetch/scan windows cover every rendered aggregate window.
- **Window validation**: If Chat output requires complete-week windows, reject explicit unsupported current windows for Chat while preserving CSV/database paths when those support custom windows.
- **Supabase storage behavior**: If Supabase is selected, missing required Supabase config should error before partial work. If Supabase is not selected, avoid requiring Supabase env just because defaults mention it.
- **Browser/local dashboard credential boundary**: For PRs adding browser-rendered dashboard views over Supabase, also use [`pr-velocity-dashboard-views-case.md`](pr-velocity-dashboard-views-case.md). Reject third-party runtime scripts on pages that handle Supabase keys, URL-query key loading, hard-coded roster lists, UTC/local week re-bucketing, overlapping Sonar buckets, and untested fallback transform logic.
- **AI-signal metadata**: Verify AI-disclosure/metadata checks pass and that raw AI signal observations are aggregated/summarized without exposing individual sensitive metadata unnecessarily.
- **Sonar enrichment**: Scope live Sonar calls/enrichment to paths that need it (for example Supabase-backed Chat runs). Missing Sonar config/token should skip with a clear diagnostic or pending context, not leak token values. Mapping gaps should be represented as pending/unmapped context.
- **Sonar PR key attribution**: Derive PR analysis keys from the raw PR number for each PR unless the external contract explicitly says otherwise; do not accidentally reuse a repo/project mapping value as the pull-request key for all PRs.
- **Malformed stored data**: Cached raw PR timestamps such as `merged_at` should fail loudly or surface pending/error context when malformed; do not silently undercount weekly merged PRs.
- **Workflow safety**: Test workflows for this area should include path filters for config/schema/testdata changes, keep read-only permissions for PR tests, and gate live schema application behind `workflow_dispatch` with secrets only in that opt-in job.

## Validation pattern

1. Refresh current PR metadata, formal reviews, inline threads, checks, and head SHA.
2. Read the linked ticket/acceptance criteria before judging whether per-user details are intended.
3. Review changed config, report orchestration, Chat renderer, Supabase store/cache, Sonar pipeline/client, workflow YAML, and tests.
4. Run local validation when the repo supports it, e.g. `git diff --check origin/<base>...HEAD`, package tests for the changed area, vet/lint, and the broader suite if feasible.
5. For large diffs, avoid unsafe `git diff | python` patterns. Write the diff to a temp file first, then run Python/grep filters over that file.
6. Treat policy-bot `.policy.yml` evaluation failures as process gates unless the PR itself changes the policy file or the failure log points to the PR diff.

## Approve-level evidence from Tools #133

- Chat renderer emitted aggregate overall/trend/context lines only; no per-user/team rows.
- Config matched the standardized Chat intent while respecting explicit flag/env overrides.
- Supabase validation was scoped to relevant report paths.
- Sonar enrichment was gated to Supabase Chat, sanitized API errors, used PR-number keys, and surfaced malformed `merged_at` instead of silently undercounting.
- Tests covered prior blocker areas: Chat scan windows, explicit Chat current-window rejection, storage backend scope, Sonar PR key attribution, empty/malformed Sonar cases, and aggregate Chat context.
- CI had relevant code/security/static/metadata checks passing; only `policy-bot: main` failed with a `.policy.yml` evaluation error, classified as a process gate.
