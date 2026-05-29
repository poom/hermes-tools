# E2E Smoke

Offline smoke test command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/my_open_prs.py --from-json 09-e2e-smoke/sample_payload.json --include-empty
```

Expected behavior:

- Prints `Waiting on Review`.
- Prints `Needs My Feedback`.
- Emits clickable Markdown PR bullets.

Live smoke command:

```bash
python3 scripts/my_open_prs.py --include-empty
```

Live mode requires `gh auth status` to pass and network access to GitHub.
