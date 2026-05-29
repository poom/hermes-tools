# Terraform/Digger WIF bootstrap PR review notes

Use this reference when reviewing Terraform PRs that bootstrap or centralize GitHub Actions Workload Identity Federation (WIF), Digger service accounts, GCS state buckets, or cross-project CI identities.

## Review sequence

1. Gather PR metadata, changed files, checks, latest reviews, review threads, and issue comments.
2. Extract the latest Digger plan comment from `github-actions[bot]`; do not rely on source diff alone.
3. Compare plan scope against the PR description:
   - Imports should match bootstrapped resources that are being adopted into Terraform.
   - Additions should match newly intended resources.
   - `0 change, 0 destroy` is important for adoption-only bootstrap paths unless explicitly justified.
4. Inspect stale/outdated review threads. If a prior blocker is verified fixed in the current diff/plan, resolve the thread rather than leaving the pending-review queue polluted.
5. Run local validation where practical: `git diff --check`, `terraform fmt -check -recursive`, `terraform init -backend=false`, `terraform validate`, `tflint`, YAML lint, and actionlint for workflow changes.
6. Run independent reviewer passes when the PR is IAM/security-sensitive, then synthesize rather than blindly reposting every note.

## WIF/Digger-specific checks

- The GitHub workflow `environment:` must match allowed `assertion.sub` entries, e.g. `repo:<owner>/<repo>:environment:<env>`.
- The workflow `workload_identity_provider` should point at the same project/pool/provider that Terraform manages. Prefer numeric project number in provider resource names and IAM principal sets.
- `google_service_account_iam_member` for `roles/iam.workloadIdentityUser` must be on the target service account, not only project IAM.
- Import blocks or bootstrap import script must include every bootstrapped resource Terraform will manage: pool, provider, service account, state bucket, service-account IAM binding, and bucket IAM members.
- GCS state bucket lifecycle semantics: to keep the most recent noncurrent version, use `num_newer_versions = 2` / JSON `numNewerVersions: 2` with noncurrent/archived state; `1` deletes the immediately previous version.
- If the stack manages resources in target projects outside the identity project, ensure the bootstrap/control-plane authority required before `digger apply` is documented and operator-approved. Custom role creation needs role-admin authority in target projects; bucket IAM management needs sufficient bucket IAM authority.
- Watch for high-privilege defaults in variable schemas (for example `roles/resourcemanager.projectIamAdmin`). If they are necessary for current entries, prefer explicit tfvars entries or a clear comment so future repos do not inherit broad IAM by accident.

## Validation notes

- If repo tooling is not active on the host, prefer reproducible one-shot tool execution (for example via mise/asdf/project tooling) rather than skipping validation. Record exact versions in the review summary when material.
- For Digger plan comments, summarize counts (`imports/adds/changes/destroys`) and call out any destroy, replacement, provider-normalized unrelated drift, or unexpected cross-project IAM/bucket mutation.

## GitHub posting

- If no blockers remain, submit a formal approval with a concise checklist of validations performed and a separate apply-readiness note if manual bootstrap grants still need to exist before apply.
- Resolve stale outdated threads only after verifying the underlying issue is fixed in the current head and/or current plan.
