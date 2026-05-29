# PR velocity dashboard views / local Supabase dashboard reviews

Use this reference for PRs that add PR-velocity dashboard SQL views, local D3/HTML dashboards, raw Supabase fallback queries, or browser-rendered engineering-throughput dashboards.

## Trigger patterns

- New `pr_velocity_*_summary` SQL views, dashboard HTML/JS/CSS, or D3/Supabase browser dashboards.
- PRs that ask users to paste a Supabase URL/API key into a local browser page.
- Follow-up PRs to ENG-964 / PR velocity reporting that expose dashboard views on top of `raw_prs`, `weekly_report_payloads`, `raw_sonar_pr_analysis`, `engineer_roster`, or sync-health tables.

## Blocking checks

1. **Browser credential trust boundary**
   - If a dashboard captures a Supabase key in an input/session storage/local storage/URL, treat the key as sensitive unless the PR proves it is a tightly scoped read-only anon key with RLS limited to the needed views.
   - Do not allow third-party runtime scripts (for example `import ... from https://cdn.jsdelivr.net/...`) to run in the same page that can read the key. Require vendored/pinned local assets, a backend/static-export flow, or a documented/read-only RLS posture with explicit trust acceptance.
   - Reject `?key=` / query-string key loading. It leaks through browser history, copied URLs, local server/proxy logs, referrers, crash reports, and screen sharing. Password-field/session-only entry is still sensitive but less bad.

2. **Canonical roster/scope source**
   - Dashboard SQL and JS fallback must not copy a hard-coded focus roster. Derive scope from canonical `engineer_roster`, `raw_weekly_pr_counts`, or materialized latest report data.
   - Honor `included_scope`, validity windows (`valid_from`/`valid_to`), bot/leadership exclusions, and team/scope metadata rather than duplicating login allowlists in multiple files.

3. **Report-window timezone contract**
   - PR velocity reporting uses Monday-Sunday Asia/Bangkok weeks. SQL views and browser fallbacks must not silently re-bucket using UTC/local browser dates.
   - Check `date_trunc('week', ... at time zone 'UTC')`, raw `(merged_at at time zone 'UTC')::date` joins, JS `new Date()` local parsing, and helpers named `weekStartUTC`. These often misclassify Sunday/Monday boundary PRs.
   - Prefer consuming canonical `raw_weekly_pr_counts` / latest report payload rows instead of reimplementing week bucketing in JS.

4. **Sonar bucket exclusivity**
   - Sonar dashboard counts should be mutually exclusive: `clean + quality_problem + pending` should not exceed the merged/analyzed denominator.
   - Classify quality problems first, then pending/error/missing rows. A PR with a blocker/high issue plus `sonar_api_error`, null gate, or `NONE` should not increment both `quality_problem_prs` and `pending_prs`.

5. **Transform tests for fallback dashboards**
   - Large handwritten dashboard files that mix credential handling, Supabase fetches, raw-table transformation, chart rendering, and formatting tend to drift from Go/SQL contracts.
   - Require small deterministic tests for scope derivation, Bangkok week windows, latest-report de-duping, Sonar status/bucket classification, and credential-handling rules (especially no `?key=`).

## Validation examples

- Local syntax/tooling: `git diff --check origin/<base>...HEAD`, `node --check <dashboard>.js`, repo Go tests/vet when PR velocity Go code exists.
- SQL/fixture tests worth requesting:
  - Insert a row with both `sonar_new_blocker_issues > 0` and `sonar_api_error != ''`; assert buckets remain mutually exclusive.
  - Insert PRs around Sunday/Monday UTC vs Bangkok boundary; assert they land in the expected Bangkok week.
  - Toggle `engineer_roster.included_scope`/validity and assert view membership changes without editing login lists.

## Case notes from EWA-Services/Tools #157

A PR adding dashboard-facing Supabase views and a local D3 dashboard was correctly reviewed as `REQUEST_CHANGES` even though `git diff --check`, `node --check`, `go test ./github`, `go vet ./github`, and `go test ./...` passed. The blockers were credential exposure via jsdelivr + pasted Supabase key, `?key=` URL leakage, hard-coded roster lists, UTC/local week bucketing vs Bangkok report weeks, overlapping Sonar buckets, and untested duplicated transform logic. An earlier concern about joining all `weekly_report_payloads` was stale after the PR switched to `pr_velocity_latest_report_payloads` and de-duped the fallback path.
