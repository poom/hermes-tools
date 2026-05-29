# Hermes cron start vs output finalization

Session-derived operational note for pending PR review cron diagnostics.

## Durable behavior

Hermes cron can advance `next_run_at` as soon as a scheduled job starts, while `last_run_at`, final status, and `<home>/.hermes/cron/output/<job-id>/*.md` are only updated when that run finishes or errors.

This means a job can look like:

- `last_run_at`: previous hour
- `next_run_at`: next hour
- no final output file for the current hour yet

…and still have actually started the current-hour run.

## Diagnostic sequence

When Poom asks why an expected hourly round did not run or why results are missing:

1. Check scheduler logs for a `Running job '<name>' (ID: <job-id>)` line around the expected time before saying the run was skipped.
2. Check active processes for the job id/name and reviewer-lane processes.
3. Check the cron output directory for a newer file only after the run has had time to finish; absence of a final file during execution is not proof of no run.
4. If a final output file exists and ends in runtime/tool-call cutoff, report it as `ran but ended error/cutoff`, not `skipped`.
5. If the job uses `deliver: local`, explain that the final digest may be local-only; only per-PR dynamic Discord messages appear when a PR was completed and explicitly delivered.

## Reporting wording

Prefer concise operational wording:

```text
It did start at <time>; next_run_at advanced when the run started. last_run_at/output update only when the run finishes, so it looked skipped while it was active/incomplete.
```

If it failed:

```text
The round ran but ended as error/cutoff, so there was no clean round-complete digest. Completed PRs with verified GitHub reviews are <...>; unfinished PRs need recovery with fresh head + duplicate-review checks.
```
