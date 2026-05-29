# Atlas Scout TA Refresh Source Tracking strict `job_id` PR case

Use when reviewing Atlas Scout / TA Refresh / Source Tracking PRs that change attribution from role/title matching to Greenhouse `job_id` matching, especially follow-ups to ENG-799 or related `greenhouse-triage` / `agent-resources` producer changes.

## Durable review pattern

1. **Treat the producer/consumer contract as the core risk.** If the PR claims sourcing rows must include `job_id`, verify the consumer truly requires `job_id`, not a legacy synonym.
2. **Search for silent fallback paths.** In `atlas_scout_reports.reports.ta_refresh.data`, `_resolve_payload_role` previously used a legacy fallback shape like:
   ```python
   job_id = _text(item.get("job_id") or item.get("greenhouse_job_id"))
   ```
   This defeats a “missing `job_id` is required DQ” contract because stale payloads carrying only `greenhouse_job_id` are accepted and counted.
3. **Probe the legacy-only row explicitly.** Passing tests may miss the bug if existing fixtures still use `greenhouse_job_id`. Add or run a small probe where a Source Tracking row has `greenhouse_job_id` but no `job_id`; expected behavior for strict-contract PRs is required DQ such as `TA-SOURCE-ROLE-NO-ID`, not attribution.
4. **Check duplicate-title attribution.** Also verify two active Forced Ranking roles with the same normalized/internal name but different Greenhouse IDs produce separate columns/counts, not a collapsed total.
5. **Check sequencing PRs.** When the body says not to merge before producer PRs land/deploy, verify linked PRs (for example `greenhouse-triage` emitting `job_id`) are merged/deployed. Treat this as process/rollout readiness separate from code blockers unless the consumer is unsafe without it.
6. **Do not duplicate equivalent unresolved inline threads.** If an existing thread already flags the legacy fallback on the same line, carry it into the formal summary and avoid a duplicate inline comment.

## Useful local commands

From `atlas-scout-reports/` in a checked-out PR:

```bash
PYTHONPATH=src python3 -m pytest tests/reports/ta_refresh/test_data.py -q
PYTHONPATH=src python3 -m pytest tests -q
```

If plain `python3 -m pytest ...` fails with `ModuleNotFoundError: atlas_scout_reports`, rerun with `PYTHONPATH=src`; this is a source-layout test invocation detail, not a code failure.

Minimal legacy-only probe:

```bash
PYTHONPATH=src python3 - <<'PY'
from atlas_scout_reports.reports.ta_refresh import data
from atlas_scout_reports.shared.data_quality import DataQualityReport

roles = data.parse_forced_ranking_universe([
    ["Ranking", "Job Name", "Department", "Assigned Recruiter", "Status", "Greenhouse Job ID"],
    ["1", "Finance Manager", "Finance", "Owner", "Active", "4420701101"],
])
dq = DataQualityReport()
matrix, _ = data.build_source_tracking_matrix(
    {"weeks": [{"label": "18 May-24 May", "start": "2026-05-18", "end": "2026-05-24"}],
     "rows": [{"week": "18 May-24 May", "position": "Finance Manager", "greenhouse_job_id": "4420701101", "source": "LinkedIn", "count": 1}]},
```

Continuation:

```bash
    {"rows": []},
    roles=roles,
    dq=dq,
)
print([(f.code, f.severity) for f in dq.findings])
print(next(row for row in matrix if row and row[0] == "LinkedIn"))
PY
```

For a strict `job_id` contract, output showing `findings []` plus a counted LinkedIn row indicates a blocker: stale legacy payloads are still accepted.

## Review wording

Blocker summary:

> `_resolve_payload_role` still falls back from missing `job_id` to legacy `greenhouse_job_id`, so stale sourcing rows are accepted and counted instead of emitting required DQ `TA-SOURCE-ROLE-NO-ID`. This defeats the PR's stated strict-`job_id` contract and the intended stale-CLI/deploy-order guardrail. Resolve only from `item.get("job_id")`; if `job_id` is absent, record required DQ regardless of whether `greenhouse_job_id` is present, and add a regression for the legacy-only row.
