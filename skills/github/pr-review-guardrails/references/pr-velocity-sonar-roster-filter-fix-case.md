# PR velocity Sonar + roster filter fix case

Use this when reviewing follow-up PRs in the PR-velocity / engineering-throughput tooling that restore or adjust Sonar filtering, roster/focus filtering, or local dashboard behavior after earlier aggregate Chat-report work.

## Trigger

- Repo/tooling resembles `github/pr_velocity*` or an internal engineering-throughput report/dashboard.
- Ticket references ENG-964, Sonar enrichment, roster filters, focus teams, or fixing dashboard/report filters.
- The PR is a follow-up to an already-reviewed PR velocity config/dashboard change and may still have stale AI-review or metadata-gate rows.

## Review checklist

1. Re-read the current Linear/ticket scope and distinguish **Chat report output** from **local/browser dashboard inspection**.
2. Verify Chat/report renderers remain aggregate-only unless the ticket explicitly authorizes person/team ranking in Chat.
3. Verify dashboard/person-grain views are local/read-only inspection surfaces, not automatically posted to Chat.
4. Check roster/focus filtering derives from canonical roster/report data instead of duplicating login allowlists or drifting from the Asia/Bangkok week contract.
5. Check Sonar state buckets are mutually exclusive and ordered correctly: quality problems should be classified before pending/error/missing, and `clean + quality_problem + pending` must not exceed the denominator.
6. Validate selected Supabase paths still require configured storage while non-Supabase paths continue to work without Supabase credentials.
7. For browser dashboard credential handling, prefer pasted/persisted form values kept within the first-party local page; block third-party script exposure, URL query-string keys, or write-capable/unscoped keys.
8. Treat old failed `finn-ai-coder` / metadata-refresh rows as process noise only after checking current-head review evidence and current code/security checks. Do not let stale process rows override an approve-level current-head code review.

## Useful local validation commands

From the Tools repo root, adapt paths if files moved:

```bash
git diff --check
go test ./github
node --check github/pr_velocity_dashboard/app.js
node --test github/pr_velocity_dashboard/data.test.mjs
```

If `gh pr checks` exits non-zero because stale rows failed, capture output with `|| true` and inspect current replacement rows/run logs before classifying the failure.

## Approve-level signals

- Local Go and Node dashboard tests pass.
- The live `base...HEAD` diff is limited to the intended report/dashboard/filter repair.
- Chat output remains aggregate-only; dashboard drilldowns are explicitly local/read-only.
- Sonar bucket classification and roster filtering are covered by tests or simple deterministic data fixtures.
- Current-head checks/reviews show no live code/security blocker; stale AI-review refresh failures are reported as process readiness only.
