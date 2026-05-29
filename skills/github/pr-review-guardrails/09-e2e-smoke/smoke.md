# E2E smoke test

Smoke test command for the same operator path used by the skill:

```bash
python3 $HERMES_HOME/skills/software-development/skillify/scripts/skillify_check.py $HERMES_HOME/skills/github/pr-review-guardrails --format markdown
python3 -m unittest $HERMES_HOME/skills/github/pr-review-guardrails/scripts/test_discord_rename_thread.py
```

Live optional command, skipped when credentials or known test PR/thread IDs are unavailable:

```bash
gh pr view PR_NUMBER --repo OWNER/REPO --json headRefOid,reviewDecision,statusCheckRollup
python3 $HERMES_HOME/skills/github/pr-review-guardrails/scripts/discord_rename_thread.py env:DISCORD_BOT_TOKEN THREAD_ID "repo #123 - Reviewing"
```
