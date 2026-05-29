# Codex telemetry ingestion tool PR case

Use this as a concrete approve-level pattern for internal developer telemetry PRs that add a local Codex/agent hook, Supabase Edge Function ingestion, Postgres/RLS schema, Grafana dashboard, and installer/bootstrap scripts.

## Review shape

- Treat the task as report-only when the requester says not to post GitHub reviews/comments or send platform messages. Return a structured result and a complete proposed formal GitHub review body/action for the parent to post after its own final head verification.
- Use live PR metadata plus local checkout evidence. Re-check the live PR head at the end and include the exact reviewed SHA in the result.
- For approval provenance, trust GitHub review API fields (`commit_id` from `pulls/*/reviews` or GraphQL review commit data) and PR `headRefOid`, not SHAs quoted inside older human/bot review bodies. Older bodies may mention an intermediate SHA while the actual review record is attached to the current head.
- If comparing a previous approval to the current head, compare `review.commit_id` to `headRefOid`. Do not use `git diff <sha-mentioned-in-body>..HEAD` unless you have verified that SHA is the review's actual commit; it can produce a huge unrelated diff and false alarm.

## Guardrail checks that supported approval

- Hook payloads contain bounded metadata/counters only: event type, timestamp, source/model metadata, repo slug, first command word, and prompt/command counters. They must not persist raw prompt text, transcripts, assistant messages, arbitrary tool output, full command text, raw hostnames, or secret-bearing remote URLs.
- Ingest token is removed from the hook process environment and excluded from child-process environments before running git/version probes or other subprocesses.
- Installer/bootstrap scripts avoid embedding tokens in generated hook code, argv, shell traces, or world-readable files; identity/config files should use restrictive permissions.
- Server-side handler requires bearer auth, handles malformed JSON without echoing the body, validates event names/timestamps/field lengths/integer bounds, maps parser failures to safe client errors, and stores `raw: {}` rather than arbitrary raw payloads.
- Supabase migration enables RLS, denies broad anon/authenticated raw access, uses a dedicated read-only dashboard role, pins search paths for security-sensitive functions/triggers, and keeps dashboard views within intended identity exposure.
- Grafana SQL uses `${var:sqlstring}` for URL-controllable variables and `$__timeFilter(...)` on selected-range panels. For high-level metrics such as Active Users, prefer querying the source event table with the dashboard time filter instead of a fixed recent-only view.
- Tests parse dashboard JSON/SQL and assert safe variable formatting, range-safe source tables/time filters, payload minimization, token env scrubbing, installer behavior, migration/RLS expectations, provisioning behavior, and handler/sanitizer failure modes.

## Validation commands used in the case

Run from the repo root unless noted:

```bash
# From codex-telemetry/
make test

# From repo root
uvx ruff check codex-telemetry
uvx ruff format --check codex-telemetry
uvx yamllint .github/workflows/codex-telemetry-grafana.yml

# From codex-telemetry smoke checks
python3 -m py_compile hook/codex_telemetry_hook.py scripts/*.py
bash -n scripts/install_codex_telemetry.sh scripts/uninstall_codex_telemetry.sh scripts/bootstrap_codex_telemetry.sh
jq empty grafana/codex-usage-dashboard.json tests/*.json
```

Pitfall: running `uvx ruff check codex-telemetry` while already inside `codex-telemetry/` fails because the path is wrong. Rerun from repo root before treating it as a code issue.

## Nonblocking notes commonly worth surfacing

- Resolve stale/outdated review threads after the current code/tests fix them, for merge hygiene.
- Document or label any intentionally fixed-window recent-activity view (for example a 30-day cap) when the dashboard picker allows wider ranges.
- Consider tightening wildcard CORS origins later; with bearer-header auth this is often hardening rather than a merge blocker.
- Separate code readiness from process gates such as pending Policy Bot or skipped non-applicable checks.
