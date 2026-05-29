# E2E Smoke

Run the same structural path an operator uses before invoking Codex.

Command:

```bash
python3 scripts/skill_health.py .
python3 -m unittest discover -s scripts -p 'test_*.py'
```

Expected result: health check and unit tests pass. Live Codex execution is intentionally skipped unless credentials and an expendable repository are available.
