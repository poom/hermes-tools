# E2E Smoke

Run the gate checker against this skill itself — the simplest end-to-end exercise.

```bash
python3 skills/skillify/scripts/skillify_check.py skills/skillify --format markdown
```

Expected: skillify passes its own gates. If a gate flips to FAIL after edits, fix it before promoting any other skill with the checker.
