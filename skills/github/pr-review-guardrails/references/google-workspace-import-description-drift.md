# Google Workspace import PRs: generated description drift

Use this when reviewing Google Workspace Terraform import PRs whose stated goal is to import existing users/groups while preserving live settings.

## Signal

A Digger/Terraform plan for imported `googleworkspace_group` resources shows entries like:

```hcl
~ resource "googleworkspace_group" "group" {
  ~ aliases = [
      + "access-matrix@finn-app.com",
    ]
  + description = "Imported existing Google Workspace group for access-matrix@ewa-services.com"
  email = "access-matrix@ewa-services.com"
  name  = "Access Matrix"
}
```

The plan may still be non-destructive (`0 to destroy`) and may preserve names/aliases, but `+ description` is a real live metadata write when the live group currently has no description.

## Review rule

For import-preserve PRs, blanket generated descriptions are request-changes-level unless the PR explicitly scopes and justifies that cleanup.

Why:

- Import PRs usually promise to preserve current Google Workspace settings by default.
- `+ description` is not list-ordering or provider normalization noise; it writes new content to production groups.
- If the author’s stated acceptance bar is “0 group name/description drift,” generic descriptions fail that bar even when alias/name drift is fixed.
- A prior approval that reasoned only about aliases/list-ordering does not cover this separate description field write.

## Evidence gathering

If the Digger plan is too large to fit in a PR comment, pull the Digger workflow log and search/count `+ description = "Imported existing Google Workspace group` snippets. Include a few examples and the count in the review body.

Also distinguish:

- `name` lines without `~`/`+`: display name is preserved.
- alias lines with both `-` and `+` for the same value nearby: likely ordering churn, not net removal.
- `+ description`: new live metadata write.

## Fix direction

- Preserve blank live descriptions as blank/null.
- Omit the `description` attribute for imported groups with no live description, or make the module default avoid generating descriptions.
- Populate descriptions only where they match live state or are intentionally enumerated in the PR scope.
- Rerun Digger and confirm the generic `+ description` lines disappear; remaining changes should be limited to imports, intended aliases/group additions, and explicitly justified metadata updates.
