# GitHub Actions PR review: action pinning policy checks

Use when reviewing PRs that modify GitHub Actions workflows, composite actions, or workflow templates in repositories with an action-pinning policy.

## Durable lesson

Some repos intentionally enforce SHA-pinned third-party GitHub Actions via a repo-owned script, pre-commit hook, or CI check. A PR that replaces 40-character SHA pins with mutable tags such as `actions/checkout@v6`, `actions/setup-node@v6`, or `SonarSource/sonarqube-scan-action@v6` can be a blocking issue even when YAML, `actionlint`, and workflow logic all pass.

Do not treat mutable major tags as acceptable just because upstream docs show them that way. First check the repository's local policy.

## Review steps

1. Search changed workflow/action files and repo scripts for pinning policy terms:
   - `manage-action-pins`
   - `action-pins`
   - `pin action`
   - `unpinned action`
   - `pre-commit`
2. If the repo has a pin-check script, run it on changed files, e.g.:
   ```bash
   bash scripts/manage-action-pins.sh check $(git diff --name-only origin/main...HEAD)
   ```
3. Treat failures as review-blocking when:
   - changed files introduce or retain unpinned external `uses:` refs, and
   - the repo policy/tool/docs still require 40-character SHA pins.
4. Remediation to request:
   - re-pin refs with the repo's pin tool, e.g. `scripts/manage-action-pins.sh pin [files...]`; or
   - if mutable tags are an intentional policy change, update the pinning policy/tool/CI/docs in the same PR so enforcement matches the new standard.

## Notes

- Self-references to the same repository's local/reusable actions may be intentionally skipped by the policy script; do not flag them solely because they use a branch/tag.
- `actionlint` does not validate org-specific pinning policy. Run both syntax checks and policy checks.
- If there are old unresolved review threads for now-fixed workflow logic, resolve them after verifying current head, then post the new review for only current blockers.
