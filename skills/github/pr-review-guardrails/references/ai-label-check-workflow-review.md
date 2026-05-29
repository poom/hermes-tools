# AI label / disclosure workflow review notes

Use for PRs that add or change GitHub Actions enforcing AI-assistance labels, PR-template disclosure sections, or org-wide synced disclosure workflows.

## Checklist

- **Trusted execution:** if the workflow runs with write permissions on PR events, prefer `pull_request_target` and verify there is no checkout/ref override to the PR head before executing local repository action code. The action/script that runs must be the trusted base-branch copy, not PR-modifiable code from the merge ref.
- **Scoped token:** verify the workflow uses the repo `GITHUB_TOKEN` with only the permissions it needs (typically `contents: read`, `pull-requests: write`, `issues: write` for labels/comments), not a PAT.
- **No untrusted execution:** PR title/body/labels should be treated as data. The workflow should not execute files, scripts, or commands from the PR head while holding write permissions.
- **Side-effect ordering:** skip rules for draft PRs, Dependabot, and trusted automation should return before creating labels, posting comments, or updating PR state.
- **Automation bypass safety:** title-based automation skips should be gated by a trusted actor; title alone must not let human PRs bypass enforcement.
- **Race-safe label seeding:** first-run label creation should tolerate concurrent `already_exists`/422 races while still surfacing other API failures.
- **Deterministic validation:** section extraction should strip HTML comments, match exact intended headers, count non-whitespace content, and enforce the required content shape without LLM judgment.
- **Markdown bullet traces:** if the policy requires a readable workflow trace, tests should cover both prose-bypass rejection and wrapped bullet continuation acceptance.
- **Shared-template rollout:** when syncing a downstream caller workflow that references a local action path, the sync manifest must include both the workflow and the action files so downstream repos do not land a broken `./.github/actions/...` reference.
- **Automation-generated PRs:** release-please or repo-file-sync PRs may need deterministic labels/body metadata or an explicit trusted skip path so the new gate does not break automation.
- **Tests:** look for tests that cover PR templates, workflow templates, action pinning, skip-before-side-effects, label races, and release/sync automation metadata.

## Non-blocker to watch

Removing auto-merge labels (for example `PR_LABELS: automerge`) from sync workflows may be intentional for safer rollout, but call it out if existing sync PRs are expected to continue auto-merging via Bulldozer or equivalent.
