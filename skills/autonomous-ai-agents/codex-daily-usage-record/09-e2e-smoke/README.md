# E2E Smoke Test

Run the same recorder script path that an operator or Hermes cron uses, against fixture Codex logs in an isolated temporary HOME under ignored `tmp/`.

Command:

```bash
python3 09-e2e-smoke/run_smoke.py
```

Pass criteria: stdout contains `E2E_SMOKE PASS`, evidence is written under `tmp/e2e-smoke/latest`, and the generated CSV/JSON contain the expected `Hermione` machine label and token totals.
