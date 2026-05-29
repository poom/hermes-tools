# Atlas Scout Reports package skeleton / executable-spec PR case

Use this reference for large PRs that combine executable implementation specs with the first Python `src/`-layout package skeleton for scheduled/reporting tools, especially when downstream phase specs depend on a shared runner contract.

## Concrete case

EWA-Services/Tools #147 evolved from docs-only consolidation specs into `feat(atlas-scout-reports): consolidation specs + PHASE 1 package skeleton` at head `de53e15e95a853016890c4882f6a11124c0815d8`.

Approve-level docs-only checks from earlier heads were no longer enough once P1 package code landed. The re-review needed to treat the package skeleton as the source of truth for all later phase ports.

## Request-changes signals from the case

Block when the P1 package code contradicts specs that land in the same PR:

- **Operator-specific secret/token paths:** shared modules hardcoded `$HOME/.codex/secrets/op_service_account_token`. Shared tooling must derive token fallback paths from `Path.home()`, env/config, or a single shared constant; do not bake one operator's home directory into package code.
- **Runner contract drift:** the spec required `heartbeat(url: str | None, *, exit_code: int)`, `runner_from_args`, and `LiveRunner(account=...)` binding selected Google Workspace account into every `gog` Sheets/Chat call. The implementation exposed `heartbeat(url: str)`, no `runner_from_args`, no account field, and bare `gog ...` commands. Treat this as blocking because downstream phase specs will call the shared runner contract.
- **No subprocess timeouts:** central wrappers around `op`, `gog`, `greenhouse`, `mcporter`, etc. used `subprocess.run` without `timeout=`. Scheduled reports can wedge indefinitely; require bounded timeout and translation of `TimeoutExpired` into the package's boundary error type.
- **Packaging/test contract gaps:** if specs say `pip install -e '.[test]'` and a Python floor (e.g. `>=3.11`), `pyproject.toml` must define the `test` extra, match `requires-python`, and make the documented test command self-contained. For `src/` layouts, record raw host pytest failure separately from `PYTHONPATH=src`/editable-install success.
- **Heartbeat URL leakage:** Checkly heartbeat URLs from `op://` refs are bearer-style monitor tokens. Failure logs must redact them; do not write full URLs to stderr/journald/CI.

## Validation pattern

1. Refresh live PR metadata, reviews, review threads, checks, and current head.
2. Read the landing spec(s) for the shared runner/package contract, not just the code.
3. Compare shared modules against spec-required signatures and construction paths.
4. Run:
   - `git diff --check origin/<base>...HEAD`
   - raw `python3 -m pytest tests -q` to detect install/path contract gaps
   - `PYTHONPATH=src python3 -m pytest tests -q` or editable install for meaningful package test signal
5. Use direct Claude CLI compact no-tools mode if the repo is large; include the spec-contract snippets and current blocker evidence.
6. Avoid duplicate inline comments when unresolved current-head threads already cover the same issue; summarize in the formal review body instead.

## Review body wording pattern

> This PR lands both executable phase specs and the P1 shared package skeleton. The package skeleton must satisfy the runner/packaging contract now, because every later port will depend on it. As written, an implementer following the specs would hit runtime `TypeError`s, ambient-account drift, host-specific secret lookup, or hung scheduled jobs, so this should be fixed before the shared contract is locked.
