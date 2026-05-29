# Preserved Codex Daily Usage Record Guide

This reference preserves the previous detailed operating guide. Use it for step-by-step procedures after the lean `SKILL.md` routes to this skill.

## Previous Frontmatter

```yaml
name: codex-daily-usage-record
description: Use when asked to check ChatGPT or Codex subscription token usage, track daily Codex token usage from local session logs, create per-machine CSV/JSON usage records, schedule Hermes cron summaries, or aggregate usage across multiple machines.
required-skills: []
required-binaries:
  - python3
version: 1.0.0
license: MIT
```

## Previous Operating Guide

# Codex Daily Usage Record

Create a repeatable daily usage record for Codex CLI local usage by scanning local Codex session logs. This does not call the Codex/OpenAI API and does not include Hermes provider calls, direct API calls, ChatGPT web/mobile sessions, or any work not executed through the Codex CLI on this machine. The output is machine-local unless records from all machines are exported and aggregated.

## Inputs

- `$machine_name`: Friendly machine label to use in reports, e.g. `Hermione`.
- `$schedule`: Optional daily cron schedule, e.g. `55 23 * * *`.
- `$delivery_target`: Optional Hermes cron delivery target, e.g. `origin`, `discord`, or `local`.
- `$codex_sessions_dir`: Optional Codex sessions path. Default: `<home>/.codex/sessions`.
- `$output_dir`: Optional output path. Default: `<home>/.hermes/usage`.

## Goal

Produce a verified per-machine daily token usage record from local Codex logs:

- `codex_daily_usage_<machine>.csv`
- `codex_daily_usage_latest_<machine>.json`
- Optional daily Hermes cron job that posts a compact summary

The record must clearly state the machine name and source scope. It must not be described as full subscription-wide usage unless every machine and every client/runtime is exporting compatible records.

## Rules

- Always label the machine in output.
- Treat Codex logs as local-machine-only and Codex-CLI-only.
- Do not claim full ChatGPT subscription usage from one machine’s logs.
- Do not imply Hermes/OpenAI provider calls, direct OpenAI API calls, ChatGPT web/mobile sessions, or separate agent runtimes are included in Codex CLI session logs.
- Prefer a friendly stable machine name, e.g. `Hermione`, over transient OS hostnames. If the user corrects the machine label, update both the live recorder and this skill so future reports use the corrected friendly name.
- Do not emit conversation message contents from Codex logs; only emit token totals and metadata.
- Use per-machine filenames to avoid overwriting records from other machines.
- Live ChatGPT/Codex rate-limit percentages may require re-authentication; local token records do not.

## Workflow

### 1. Inspect Codex Availability

Check whether Codex CLI is installed and whether it is logged in:

```bash
which codex || true
codex login status 2>&1
```

If live checks fail with expired ChatGPT auth, continue with local log scanning and report that live rate-limit data is unavailable until re-login.

**Success criteria**: You know whether Codex is installed, whether ChatGPT auth is currently usable, and whether local logs are still available.

### 2. Inspect Local Codex Logs

Look for token usage fields in local Codex session JSONL files under:

```text
<home>/.codex/sessions
```

Useful fields include:

- `payload.info.total_token_usage.input_tokens`
- `payload.info.total_token_usage.cached_input_tokens`
- `payload.info.total_token_usage.output_tokens`
- `payload.info.total_token_usage.reasoning_output_tokens`
- `payload.info.total_token_usage.total_tokens`
- `payload.rate_limits.primary.used_percent`
- `payload.rate_limits.secondary.used_percent`
- `payload.rate_limits.plan_type`

**Success criteria**: At least one local session log with `total_token_usage` is found, or the user is told that no local usage logs exist on this machine.

### 3. Install the Daily Recorder Script

Use the bundled helper script:

```text
scripts/codex_daily_usage_record.py
```

Install it to Hermes' script directory:

```bash
mkdir -p <home>/.hermes/scripts
cp scripts/codex_daily_usage_record.py <home>/.hermes/scripts/codex_daily_usage_record.py
chmod +x <home>/.hermes/scripts/codex_daily_usage_record.py
```

The script scans `<home>/.codex/sessions/**/*.jsonl`, parses token accounting fields, aggregates by local calendar day, and writes. It never calls Codex or OpenAI APIs; it only reads already-written Codex CLI session logs:

- `<home>/.hermes/usage/codex_daily_usage_<machine>.csv`
- `<home>/.hermes/usage/codex_daily_usage_latest_<machine>.json`

Machine naming supports an explicit override:

```bash
CODEX_USAGE_MACHINE_ID=Hermione python3 <home>/.hermes/scripts/codex_daily_usage_record.py
```

**Success criteria**: The skill folder contains `scripts/codex_daily_usage_record.py`, the installed script exists at `<home>/.hermes/scripts/codex_daily_usage_record.py`, and running it produces per-machine CSV/JSON files and prints `Machine: <machine_name>`.

### 4. Backfill and Verify

Run the script once manually:

```bash
chmod +x <home>/.hermes/scripts/codex_daily_usage_record.py
<home>/.hermes/scripts/codex_daily_usage_record.py
```

Inspect the first rows:

```bash
sed -n '1,5p' <home>/.hermes/usage/codex_daily_usage_<machine>.csv
```

Verify the CSV contains `machine`, `day`, `sessions`, `total_tokens`, `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_output_tokens`, and `models`.

**Success criteria**: The CSV has daily rows and the machine column uses the friendly machine name.

### 5. Schedule Daily Recording

If the user wants ongoing records, create a no-agent Hermes cron job via the cron tool:

```yaml
name: Daily Codex token usage record
schedule: "55 23 * * *"
script: "codex_daily_usage_record.py"
no_agent: true
deliver: origin
repeat: forever
```

Use `deliver: origin` if the user wants reports back in the requesting chat/thread. Use `deliver: local` if the user only wants files updated silently.

**Success criteria**: `hermes cron list` shows an enabled job with the expected schedule, script, and delivery target.

### 6. Explain Multi-Machine Scope

Tell the user clearly:

- This machine’s record only includes this machine’s local Codex CLI logs.
- Usage from this Hermes chat, direct OpenAI API calls, ChatGPT web/mobile, or any non-Codex-CLI runtime will not appear in these logs unless that runtime also writes compatible records.
- To track all machines, install the same recorder on every machine.
- Each machine should use a unique friendly machine name.
- Sync all per-machine CSV files to a shared folder, Git repo, Drive folder, or other central location before aggregating totals.

**Success criteria**: The user understands whether the current report is single-machine or multi-machine.

### 7. Optional: Aggregate Across Machines

If a shared folder is available, write an aggregator that reads `codex_daily_usage_*.csv`, groups by day and optionally by machine, and warns when an expected machine has no row for a day.

**Success criteria**: The aggregate report distinguishes all-machine totals from per-machine totals and warns when data is incomplete.

## Failure Behavior

### No local logs

If `<home>/.codex/sessions` does not exist or has no usage fields, report that this machine has no local Codex usage history. The script still writes empty CSV/JSON outputs.

### Expired ChatGPT auth

If Codex live checks fail with refresh token errors, local daily records can still be produced. Tell the user to re-authenticate only if they need live rate-limit percentages:

```bash
codex logout
codex login
```

### Wrong machine name

If the OS hostname is not the desired reporting name, set:

```bash
CODEX_USAGE_MACHINE_ID=<friendly-name>
```

Or add a hostname alias in the script.

### Duplicate or stale files

Do not overwrite another machine’s file. Use machine-specific filenames. If a machine is renamed, either keep the old file for history or migrate it intentionally.

## Scripts

- `scripts/codex_daily_usage_record.py` — deterministic recorder used by both manual operators and Hermes cron.
- `scripts/test_codex_daily_usage_record.py` — offline unit tests for parsing, aggregation, machine naming, and output writing.

## Validation Commands

Run the full offline validation suite from this skill directory:

```bash
python3 -m unittest discover scripts
python3 04-integration-tests/test_codex_daily_usage_record_integration.py
python3 09-e2e-smoke/run_smoke.py
```

Run the Skillify gate checker from the repository root or with an absolute skill path:

```bash
python3 $HERMES_HOME/skills/software-development/skillify/scripts/skillify_check.py $HERMES_HOME/skills/autonomous-ai-agents/codex-daily-usage-record --format markdown
```

## Resolver Coverage

- `agents/openai.yaml` gives resolver-visible metadata for OpenAI-style runtimes.
- `07-resolver-evals/resolver_trigger_eval.md` lists should-trigger and should-not-trigger prompts.

## LLM Evaluation Policy

This skill has no LLM-owned production judgment: the token parsing, aggregation, and output rendering are deterministic. `05-llm-evals/no_llm_owned_judgment.md` records the rubric/golden-case waiver so future changes add a real judge if an LLM-owned summary, classifier, or recommendation step is introduced.

## Invocation Examples

Use this skill when the user says:

- “Can you check token usage from ChatGPT subscription?”
- “Can we keep this record daily?”
- “Track Codex token usage by day.”
- “Make a daily token usage CSV.”
- “Can we aggregate token usage across machines?”
