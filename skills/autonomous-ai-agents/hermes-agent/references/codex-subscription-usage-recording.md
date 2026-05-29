# Codex / ChatGPT subscription usage recording

Use this when the user asks to keep daily records of ChatGPT subscription / Codex token usage.

## Key distinction

- OpenAI API billing has a platform usage dashboard.
- ChatGPT subscription / Codex usage is different: locally available evidence comes from Codex JSONL session logs under `<home>/.codex/sessions/` plus occasional `rate_limits` snapshots in those logs.
- This is machine-local. One machine's `<home>/.codex/sessions/` does not include usage from other machines.

## Local daily recorder pattern

Create a deterministic `no_agent` cron script under `<home>/.hermes/scripts/`, e.g. `codex_daily_usage_record.py`, that:

1. Scans `<home>/.codex/sessions/**/*.jsonl`.
2. For each session file, reads only metadata fields and usage objects, not message contents.
3. Takes the maximum `payload.info.total_token_usage.total_tokens` seen per session file to avoid double counting incremental updates within one session.
4. Aggregates by local calendar day.
5. Writes idempotent outputs under `<home>/.hermes/usage/`.
6. Prints a compact summary for cron delivery.

Usage fields observed in Codex logs:

```text
payload.info.total_token_usage.input_tokens
payload.info.total_token_usage.cached_input_tokens
payload.info.total_token_usage.output_tokens
payload.info.total_token_usage.reasoning_output_tokens
payload.info.total_token_usage.total_tokens
payload.rate_limits.primary.used_percent
payload.rate_limits.secondary.used_percent
payload.rate_limits.plan_type
```

## Multi-machine pitfall

Daily usage records are local unless every Codex machine runs the recorder. Include a machine ID in filenames and rows:

```text
<home>/.hermes/usage/codex_daily_usage_<machine>.csv
<home>/.hermes/usage/codex_daily_usage_latest_<machine>.json
```

Derive `<machine>` from `CODEX_USAGE_MACHINE_ID` or `socket.gethostname()` sanitized for filenames. Print `Machine: <machine>` in the cron output so Discord summaries are not mistaken for all-account totals.

To get account-wide totals, install the same recorder on each machine and sync the per-machine CSVs to a shared folder, Drive, Git repo, or object store; then aggregate the synced CSVs by day.

## Cron setup

For a deterministic daily record, use a no-agent Hermes cron job:

```bash
hermes cron create '55 23 * * *'
# or via cronjob tool:
# action=create, name='Daily Codex token usage record', schedule='55 23 * * *',
# script='codex_daily_usage_record.py', no_agent=true, deliver='origin'
```

Verify with:

```bash
hermes cron list
<home>/.hermes/scripts/codex_daily_usage_record.py
head <home>/.hermes/usage/codex_daily_usage_*.csv
```

## Auth notes

The recorder does not require live Codex/ChatGPT auth because it reads local logs. Live rate-limit checks may fail with errors like `refresh_token_reused` / `token_expired`; ask the user to re-login with `codex logout && codex login` if current live limits are required.
