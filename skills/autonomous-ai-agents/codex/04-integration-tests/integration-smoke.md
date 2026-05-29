# Integration Smoke

INTEGRATION_TEST: Run this check in a checkout that has the Codex CLI available. It is offline by default and does not call Codex.

Command:

```bash
python3 scripts/skill_health.py .
```

Expected result: the command prints `codex skill health ok`. If Codex credentials are absent, skip any live Codex command and keep this structural smoke as the integration baseline.
