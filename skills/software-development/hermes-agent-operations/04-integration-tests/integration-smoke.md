# Integration Smoke

INTEGRATION_TEST: Run this structural check in a checkout with the skill installed. It is offline by default and skips live endpoints when credentials are absent.

Command:

```bash
python3 scripts/skill_health.py .
```

Expected result: the command prints `hermes-agent-operations skill health ok`. If live credentials are absent, skip live side effects and keep this structural check as the integration baseline.
