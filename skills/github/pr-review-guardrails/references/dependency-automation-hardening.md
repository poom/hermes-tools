# Dependency automation hardening notes

Use this reference when reviewing PRs that add or modify Dependabot, Renovate, package-update bots, or org-wide dependency update templates.

## Dependabot cooldown / minimum release age

GitHub Dependabot supports a `cooldown` option for version updates. It delays update PRs for newly released versions and can reduce exposure to hijacked packages, compromised maintainers, or malicious releases that are discovered shortly after publication.

Useful keys:

```yaml
cooldown:
  default-days: 7
  semver-patch-days: 7
  semver-minor-days: 14
  semver-major-days: 30
```

Notes:
- Applies to version updates, not security updates.
- Supports SemVer-aware delays for ecosystems such as npm/yarn, pip, Composer, Docker, Go modules, Terraform/OpenTofu, GitHub Actions, and others documented by GitHub.
- `exclude` entries take precedence over `include` entries.
- Absence of cooldown is usually a security-hardening recommendation, not automatically a merge blocker, when dependency PRs still require human review and CI.
- For org-wide templates or automerge-enabled repos, consider escalating missing cooldown/minimum release-age to a blocker or at least a high-priority finding.

## Review heuristic

When a PR enables dependency automation broadly:
1. Check whether updates are just opened as PRs or can be auto-merged.
2. Check cadence, PR limits, grouping, allow/ignore rules, and directory coverage.
3. Check whether a minimum release age / cooldown exists.
4. If the repo already has an equivalent grace-period policy elsewhere, recommend mirroring it for consistency.
5. Call out inaccurate PR descriptions that claim tests/config coverage not present in the diff.
