# E2E Smoke

Run the same structural path an operator uses before applying this skill to live work.

Command:

```bash
python3 scripts/skill_health.py .
python3 -m unittest discover -s scripts -p 'test_*.py'
```

Expected result: the health check and offline unit tests pass. Live side effects remain skipped unless the operator has the required credentials and target system.
