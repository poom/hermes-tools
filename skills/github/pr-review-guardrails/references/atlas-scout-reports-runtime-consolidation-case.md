# Atlas Scout Reports runtime consolidation PR case

Use this reference for large `atlas-scout-reports` consolidation/port PRs that combine multiple report phases, shared runner changes, readback fixes, and live Google Chat/Sheets delivery paths.

## Concrete case

EWA-Services/Tools #172 (`feat(atlas-scout-reports): complete consolidation (P5-P9 + readback sweep) [ENG-799]`) at head `d94d1987a51084458ddbb868534748da435c209a` looked healthy at a coarse level: main tests/pre-commit/static/security/AI-label checks were mostly green and the isolated atlas-scout suite passed (`290 passed`). The correct verdict was still **REQUEST_CHANGES** because live-runtime contracts and PII-safe error handling were broken.

## Blocking signals from the case

Block when any of these are present in current code or unresolved current-head threads:

- **Runner errors leak report payloads.** `RunnerError` formats raw argv/stderr while live `gog` commands carry Chat bodies in `--text` and Sheets matrices/candidate data in `--values-json`. Non-zero exits can dump sensitive candidate/report content into logs or tracebacks. Require redaction of sensitive flags and stderr before formatting errors, with tests.
- **Runner failures escape the controlled CLI path.** If `RunnerError` no longer subclasses the boundary error the CLI catches (for example `StructuralConfigError`), failures become uncaught tracebacks and amplify the payload leak. Require either restored exception hierarchy or explicit CLI catch/tests.
- **Google Chat response envelope mismatch.** Verify live `gog chat messages send --json` shape against all consumers. In #172, tests elsewhere modeled `{"message": {"name": ..., "thread": {"name": ...}}}`, while `deliver_thread()` read top-level `name`/`thread`, causing partial delivery: starter message sent, then failure before reply/heartbeat. Require nested-envelope support and regression tests.
- **Sheets writes without clearing stale ranges.** `gog sheets update` at `A1` overwrites only the new matrix span. If prior output was larger, stale rows/columns remain visible and can poison readback/report output. Require clear-before-write, blank-fill over the configured clear range, or a proven downstream clear applier; add a shrink-case test.
- **Secret-like heartbeat URL logging.** Treat Checkly/heartbeat ping URLs as operational tokens. Failure logs should redact raw URL/token values and exception text that echoes them.
- **Unbounded external CLI calls.** Shared wrappers around `greenhouse`, `gog`, `mcporter`, `op`, etc. should use bounded `timeout=` and translate `TimeoutExpired` into the controlled error path. A hung external command can wedge scheduled reports indefinitely.
- **Dropped account override.** If report CLIs accept `--account` / `GOG_ACCOUNT`, ensure `runner_from_args()` passes the selected account into the live runner or document/test why a particular path intentionally uses the default account.

## Validation pattern

1. Refresh live PR metadata, comments, formal reviews, review threads, checks, and head SHA.
2. Use GraphQL review-thread fallback when `gh pr view --json reviewThreads` is unavailable; unresolved current-head inline threads are first-class evidence.
3. Do not duplicate inline comments for already-open blocker threads. In the formal review body, say that the unresolved current-head threads remain blocking and summarize the issues.
4. Run the report suite in the repo-supported environment or a temporary isolated editable install if the host environment lacks package setup. Record the passing suite as positive evidence, but do not let it override live-contract blockers.
5. For Reviewer B, a compact no-tools Claude prompt with selected files/snippets is enough: include PR URL/title/head, current checks, known suspected blockers, and the relevant `runner.py`, Chat delivery, Sheets, heartbeat, CLI, and tests snippets.
6. Re-check the head immediately before posting. Submit a full `Guardrail review — Needs changes` body and verify through the pulls reviews API that Poom has a current-head `CHANGES_REQUESTED` review.

## Review body wording pattern

> I’m requesting changes because several current-head blocker threads remain valid. The test suite is useful evidence for the migrated reports, but it does not cover the live runtime contracts: runner errors can leak Chat/Sheets payloads into logs, Chat delivery consumes the wrong response envelope, and sheet rewrites can leave stale rows after shrink. Please fix and add regression coverage before merge.
