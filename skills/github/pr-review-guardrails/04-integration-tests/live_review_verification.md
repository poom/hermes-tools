# PR review guardrails integration test

INTEGRATION_TEST / LIVE_TEST marker.

Purpose: prove live GitHub review verification and posting preflight commands work when credentials are present.

Credential skip behavior: if `gh auth status` fails, skip live GitHub checks. If `DISCORD_BOT_TOKEN` is missing, skip the Discord thread rename live path and rely on the offline unit test for request construction.

Example live commands:

```bash
gh pr view PR_NUMBER --repo OWNER/REPO --json headRefOid,baseRefName,reviewDecision,statusCheckRollup
python3 scripts/discord_rename_thread.py env:DISCORD_BOT_TOKEN THREAD_ID "repo #123 - Reviewing"
```
