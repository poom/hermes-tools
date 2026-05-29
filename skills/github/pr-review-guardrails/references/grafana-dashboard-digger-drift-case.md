# Grafana dashboard Terraform PRs with unrelated Digger datasource drift

Use this reference when a Terraform PR adds or updates a Grafana dashboard and the code diff is scoped, but Digger/Terraform plan output includes unrelated production datasource or shared-resource mutations.

## Case pattern

A PR added a new Grafana dashboard via a wrapper module. Local/static checks were clean:

- Dashboard JSON parsed with `jq empty`.
- `git diff --check` passed.
- The Terraform/dashboard diff itself was scoped and reasonable.
- Review threads had no unresolved code-specific blocker.

The latest Digger plan, however, still included production mutations outside the dashboard scope: `1 to add, 2 to change`, where the add was the new dashboard and the two changes were existing shared Grafana Supabase datasource resources changing type from `grafana-postgresql-datasource` to `postgres`.

The author explained that the datasource drift came from an earlier unapplied PR. That explanation established provenance, but it did **not** make the current apply safe: `digger apply` from this PR would still apply those unrelated production datasource changes together with the dashboard.

## Review rule

For dashboard-only or dashboard-scoped Terraform PRs:

1. Treat a scoped dashboard diff as approve-level only after checking the current Digger/Terraform plan.
2. If production plan output contains unrelated mutations to existing shared datasources or other resources, keep/request changes unless one of these is true:
   - a fresh plan removes the unrelated mutations;
   - the unrelated mutations are split/applied separately; or
   - an explicit production owner accepts that applying those mutations together with this PR is expected and safe.
3. An author explanation that drift originated elsewhere is not sufficient by itself. The current apply plan is the merge-safety contract.
4. Separate process gates from code findings: policy-bot failures or pending `digger/apply` can be merge/process readiness notes, but unrelated production mutations in the apply plan are a review blocker.

## Suggested review wording

> The Terraform/dashboard diff is scoped, and the dashboard JSON/static checks look fine, but I still can’t approve the current head because the latest production Digger plan is not scoped to this dashboard. It would create the dashboard and also mutate existing shared Grafana datasource resources. Please either refresh/reconcile the plan so this PR only applies the dashboard, split/apply the unrelated datasource drift separately, or get explicit production-owner sign-off that applying those datasource type migrations with this dashboard is intentional and safe.
