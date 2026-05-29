# E2E smoke test

Smoke test command for the same operator path used by the skill:

```bash
python3 $HERMES_HOME/skills/software-development/skillify/scripts/skillify_check.py $HERMES_HOME/skills/github/pending-pr-review --format markdown
bash $HERMES_HOME/skills/github/pending-pr-review/scripts/test_list_pending_prs.sh
```

Live optional command, skipped when `gh auth status` is unavailable:

```bash
bash $HERMES_HOME/skills/github/pending-pr-review/scripts/list_pending_prs.sh --json --owner ewa-services --reviewer poom --limit 20
```
