# GitHub PR review SLA alert workflow reviews

Use this reference for PRs that change GitHub PR-review SLA probes/reporters, Google Chat SLA alerts, or workflow tests that guard those scripts. Concrete case: `EWA-Services/Tools#178` (`ENG-1042`) fixed a false-negative PR Review SLA alert where the scheduled scan inspected only the first page of matching PRs and skipped team requests.

## Review focus

- **Scan completeness**: A limit increase alone is not enough. Verify the probe records and emits enough coverage metadata to distinguish a complete clean scan from a truncated scan, e.g. `matched_prs`, `visited_prs`, `scanned_prs`, and `truncated`.
- **No clean-looking incomplete alerts**: If the scan truncates with zero findings, the Chat payload must explicitly say the scan was incomplete rather than “no outstanding reviewer requests.” If it truncates with findings, prefer surfacing that the displayed set may be incomplete as a hardening follow-up.
- **User vs team review requests**: Team requests should not be blanket-skipped. If the probe cannot map teams to members, validate that it reports team requests and relies on GitHub’s current request state/removal semantics to clear satisfied team requests.
- **Bot/requestee exclusion**: Configured bot reviewers and conventional `[bot]` accounts should be excluded consistently from both reviewer-count thresholds and outstanding request rows; avoid accidentally skipping real teams because bot filtering is user-only.
- **Bounded Chat output with full logs**: Chat cards should cap the number of rendered PR groups (for example `--max-prs`) but keep the full findings in workflow logs / JSON output. The cap text should be distinguishable from scan truncation.
- **Workflow path filters and test ownership**: If a workflow narrows `pytest tests` to a hardcoded test-file list, verify path filters only include sources whose tests are in that list, or the list still includes all tests for the triggered source paths. Existing review threads around missing path filters can be fixed by adding both the relevant source files and the previously owned tests.
- **Process gates**: Treat Policy Bot human-review requirements as process gates unless the PR changes policy files or the failing gate points to the PR diff.

## Validation pattern

1. Read the linked ticket/acceptance criteria and PR body; identify the stated failure mode (for Tools #178: 100-of-741 scan false negative plus skipped team requests).
2. Refresh current PR metadata, head SHA, changed files, checks, issue comments, formal reviews, and review threads.
3. Review probe logic for pagination/limit accounting, bot exclusions, team request handling, stale/active bucketing, and JSON/log output.
4. Review Chat renderer logic for no-findings, findings, capped-display, and truncation cases.
5. Review workflow path filters and test command scoping together; do not look at either in isolation.
6. Run focused tests with the workflow’s dependency set. If the host environment lacks a dependency such as `requests`, use an isolated fallback matching CI, e.g. `uv run --isolated --python 3.11 --with pytest --with requests pytest <focused tests> -q`.
7. Run focused Ruff/check formatting plus `git diff --check` when applicable.
8. Recheck the live head immediately before returning/posting a verdict.

## Approve-level evidence from Tools #178

- The scheduled workflow changed `--limit 100` to `--limit 1000` and the probe emitted `matched_prs`, `visited_prs`, `scanned_prs`, and `truncated`.
- The reporter no-findings path explicitly returned a scan-incomplete warning when `truncated` was true.
- The probe reported team requests via `reviewer_type: team` and skipped configured bot users / `[bot]` accounts.
- The Chat reporter added `--max-prs` and a “Showing N of M PRs” footer while preserving full findings in logs/JSON.
- Existing workflow review threads were resolved by adding source path filters for `github/pr_review_*` files and keeping `tests/test_linear_projects_reporter.py` in the focused pytest list.
- Local validation passed with isolated pytest + requests (`34 passed`), focused Ruff, and `git diff --check`; remote CI was green except for expected Policy Bot human approval.

## Non-blocking hardening notes

- A card with findings plus `truncated=true` can still benefit from a visible incomplete-scan banner, even if the current increased limit covers the incident data set.
- Setting `truncated=true` exactly when `fetched == limit` can false-positive if there are no more pages; refine only if it affects operational trust.
- Hardcoded workflow test lists are maintenance traps: future root-level tests may not run even though `tests/**` triggers the workflow unless the list is updated.
