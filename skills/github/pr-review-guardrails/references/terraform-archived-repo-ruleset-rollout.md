# Terraform archived-repository ruleset rollout failures

Session source: EWA-Services/github-infrastructure PR #334 review (May 2026).

Use this when reviewing Terraform PRs that change GitHub repository rulesets, branch protection, bypass actors, required checks, or other org-wide repository settings.

## Pattern

A module-level change fans out across many repositories and looks safe in source diff and plan shape, for example:

```text
Plan: 0 to add, 100 to change, 0 to destroy.
```

But `digger apply` fails after partial modifications because GitHub rejects ruleset updates on archived repositories:

```text
Error: PUT https://api.github.com/repos/EWA-Services/Branding/rulesets/9480816: 403 Repository was archived so is read-only. []
```

Concrete PR #334 case:
- Diff changed `modules/finn-github-repository/main.tf` so `core_protection_ruleset` got `bot_bypass_team_id = var.bot_bypass_team_id` for all protected branches.
- Intended safety was sound: `bypass_mode = "always"` stayed gated to `!var.trunk_based_development && each.key == "develop"`, while main/default branches got `pull_request` mode only.
- Digger plan passed with `0 add, 100 change, 0 destroy`.
- Digger apply failed on archived repos (`Branding`, `Advance-Fee-Calculator`, `Charge-Times-Calculator`, `Anomaly-Detection`, `RiREDACTED_SECRET_PATTERN`) because they still passed `bot_bypass_team_id` and GitHub refused ruleset PUTs.

## Review rule

Treat this as a request-changes-level blocker, not merely process noise, when:

1. The PR's desired state includes ruleset/protection changes for archived repositories, and
2. Live Digger apply has failed or would predictably fail with archived/read-only errors.

Why it matters:
- Apply may already be partially complete, leaving drift between Terraform state, plan, and GitHub.
- Future applies will continue to fail until archived repos are excluded or their desired ruleset changes are made inert.
- Merge would preserve an unappliable desired state.

## What to check

- Search repository configs for archived repositories that still opt into the changed module behavior:
  ```bash
  rg -n 'archived\s*=\s*true|bot_bypass_team_id|ruleset_enforcement_active|enable_policybot' repository-*.tf
  ```
- Cross-check failed Digger log repo names against `repository-*.tf` module blocks.
- Inspect the latest Digger plan and apply output, not just source diff.
- If apply failed after partial modifications, pull failing logs with:
  ```bash
  gh run view RUN_ID --repo OWNER/REPO --log-failed
  ```

## Fix direction to request

Ask the author to do one of the following, depending on repo policy:

- Preserve previous behavior for archived repositories for the new fan-out change.
- Exclude archived repositories from the changed ruleset/protection module path.
- Set the new bypass/ruleset inputs to `null`/disabled for archived repositories.
- Remove/adjust Terraform management of read-only archived rulesets if that is the established operational policy.

Then require a fresh Digger plan and successful Digger apply before approval/merge.

## Non-blocking distinction

A source-level security concern may be resolved even while apply is blocked. In PR #334, the earlier `bypass_mode = "always"` issue was fixed and the PR-mode bypass model was acceptable, but the archived-repo apply failure remained blocking for merge readiness.

## Re-review resolution pattern

When re-reviewing after an archived-repo failure, check both the immediate failed archived repos **and** future archive transitions:

1. If the author simply excludes `archived = true` repos from the new ruleset input after a partial apply, inspect the next Digger plan. It may still show changes for the already-partially-mutated archived repos, which would still fail read-only apply.
2. If the author special-cases the currently-mutated archived repos to reach `0` changes, check whether future active-to-archived transitions would flip the same input off after archival. If so, the next archive transition can recreate the same `403` failure.
3. A robust fix is often to keep the ruleset input stable across archive transitions (for example, do not derive `bot_bypass_team_id` from `archived`) so archiving a repository does not create a post-archive ruleset diff.
4. Once current-head code evidence plus Digger show the archived blocker is substantively resolved, approve from a code-review perspective but report remaining process gates separately (for example `digger/apply` still pending). Resolve the stale/outdated inline review thread if it was yours and no unresolved discussion remains.

Concrete PR #334 follow-up:
- `dccbd69` excluded archived repos, but Digger still planned 5 updates against already-mutated archived rulesets.
- `36954f4` reconciled the five archived repos to `0` plan changes, but still made future archive transitions unsafe by flipping the input on archival.
- `a4c8967` removed the archive-state conditional and kept `bot_bypass_team_id = var.bot_bypass_team_id`; latest plan was `+0 ~0 -0`, reviewers agreed the blocker was resolved, and the final review could be `APPROVE` with `digger/apply`/stale bot gates called out as process follow-ups.
