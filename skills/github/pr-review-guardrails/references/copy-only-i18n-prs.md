# Copy-only i18n / user-facing wording PR reviews

Use this when a PR claims to change only translated/user-facing copy while preserving runtime contracts (for example renaming a label such as "Loan Purpose" to "Intended Use" in locale JSON files).

## Review checklist

1. **Confirm scope is truly copy-only**
   - Diff should be limited to locale/resource files or explicitly scoped docs/comments.
   - Verify no TypeScript/templates/backend code, form controls, payload/API fields, analytics event names, enum names, or i18n keys were renamed unless the ticket explicitly asks for that migration.
   - For Angular/Ionic repos, search render paths for the changed keys (e.g. `WITHDRAW_MONEY.LOAN_PURPOSE.LABEL`) and verify the templates/components use the values the PR changed.

2. **Map strings back to the ticket**
   - Read the linked ticket acceptance criteria and country/locale scope.
   - Check each user-visible surface called out by the ticket: initial label/eyebrow, section headings, summary/readback labels, disclosure/mandate screens, and any locale variants that may be enabled later.
   - If a locale intentionally lacks a corresponding key, record that as existing structure rather than inventing a missing-change blocker.

3. **Search for stale old wording carefully**
   - Repo-wide old-copy matches are not automatically blockers. Classify each remaining match:
     - current user-visible UI copy in the affected flow → usually blocking if the ticket required a full rename;
     - backend validation/error message shown to users → check exposure path and ticket wording;
     - internal logs/emails, code identifiers, analytics names, payload fields, or comments → usually non-blocking when the PR explicitly preserves identifiers/contracts.
   - Do not require renaming `loanPurpose`-style internal identifiers when the ticket says to keep payload/API/analytics fields unchanged.

4. **Validate resource files**
   - Run syntax checks for the changed formats, e.g. `jq empty <changed-json-files>` for JSON locales.
   - Run whitespace checks: `git diff --check <base>...HEAD`.
   - Prefer remote CI/test gates for broad app validation; local full Angular/Karma/devcontainer runs may be unnecessary for a tiny copy-only JSON diff if the current remote frontend/functions tests and pre-commit pass.

5. **Experiment / feature flag handling**
   - A pure copy rename usually does not need a feature flag or experiment outcome.
   - Still check PR comments/body for an explicit no-experiment/safe-rollout approval when the repository has GrowthBook or metadata gates.

## Approve-level signals

- Changed files are limited to locale/resource files.
- Ticket-required visible labels/headings/readback strings are updated in all required locales/surfaces.
- Identifiers and runtime contracts are preserved when required.
- Syntax/whitespace validation passes and remote tests/security/quality gates are green.
- Remaining old wording is limited to intentionally preserved identifiers, non-rendered comments, or internal-only logs/errors.

## Non-blocking caveats to mention

- PolicyBot or required human review may still block merge even when the code is approve-level.
- If the canonical devcontainer/local harness cannot run because a private secrets tool such as `op` is missing, record the limitation and rely on current remote CI only when it covers the same changed files sufficiently.
