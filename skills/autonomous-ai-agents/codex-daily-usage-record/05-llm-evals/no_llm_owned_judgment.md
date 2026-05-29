# No LLM-Owned Judgment Evaluation

This skill currently has no LLM-owned production judgment. Token extraction, daily aggregation, CSV/JSON rendering, and cron execution are deterministic and covered by `scripts/test_codex_daily_usage_record.py`, `04-integration-tests/test_codex_daily_usage_record_integration.py`, and `09-e2e-smoke/run_smoke.py`.

## Rubric

A future change needs a real LLM judge if it adds any step where a model chooses, classifies, summarizes, compares, or recommends. Examples that would require a judge:

- An LLM-written narrative summary of daily usage.
- An LLM classification of whether usage is anomalous.
- An LLM recommendation about changing plans or moving work between machines.

A change does not need a judge when it only modifies deterministic parsing, arithmetic, file naming, cron wiring, or schema validation.

## Golden cases

Expected deterministic cases for the current no-LLM workflow:

1. Given fixture Codex JSONL records with token fields, expected output is exact numeric CSV/JSON totals.
2. Given no local logs, expected output is empty CSV/JSON files and a no-logs message.
3. Given a friendly machine override, expected output uses that machine label in file names and payloads.

If a future LLM-owned step is introduced, replace this waiver with `golden_cases.json`, a rubric Markdown file, and a judge harness that can run in replay mode without credentials.
