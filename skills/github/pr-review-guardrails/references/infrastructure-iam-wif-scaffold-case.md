# Infrastructure IAM WIF scaffold PR case

Use this reference for large first-run/central `infrastructure-iam` PRs that scaffold GitHub Actions WIF, Digger CI identities, GCP service accounts, AWS OIDC roles, and Terraform state buckets across multiple roots.

## Approval-level evidence from the case

A guardrail approval is reasonable when all of these hold on the current head:

- Current Digger plans are posted and green for every affected root/project, not just one provider:
  - GCP identity root (`gcp-finn-identity-core` or equivalent) is green.
  - AWS production/root plan is green.
  - Plans have no unexplained destroys/replacements. Imports and in-place tag/description/policy adoption are acceptable when they match documented bootstrap/adoption scope.
- The GitHub workflow routes provider setup by project type correctly:
  - GCP auth runs only for GCP Digger projects and points to the current identity project/provider/service account.
  - AWS setup is a GitHub expression, e.g. `setup-aws: ${{ contains(fromJSON(inputs.spec).job.projectName, 'aws') }}`, not a literal string passed through to Digger.
  - The GitHub job `environment:` matches the `repo:ORG/REPO:environment:ENV` subjects used in WIF/OIDC conditions.
- WIF/OIDC trust boundaries are exact:
  - GCP provider allowed subjects are explicit repo/environment subjects, not org-wide wildcards.
  - AWS role trust conditions use exact `token.actions.githubusercontent.com:sub` and `aud` values.
  - Downstream repository roles are separately scoped to their repository/environment and state prefixes.
- Bootstrap/adoption lifecycle is covered:
  - Import blocks or import instructions cover every bootstrapped resource Terraform will now manage.
  - Durable bootstrap grants are either Terraform-managed or explicitly documented as operator-approved control-plane prerequisites with a lifecycle/removal path.
  - Cross-project permissions needed before apply are documented for each target project and shared state bucket.
- Known provider/API permission pitfalls are fixed in both Terraform and bootstrap scripts:
  - GCS lifecycle keeps a recovery version with `num_newer_versions = 2` and mirrored JSON `numNewerVersions: 2` when that is the stated policy.
  - AWS Terraform state encryption permissions use `s3:GetEncryptionConfiguration` / `s3:PutEncryptionConfiguration`, not non-authorizing `GetBucketEncryption` / `PutBucketEncryption` action names.
  - AWS IAM tag refresh/tagging includes `iam:ListOpenIDConnectProviderTags` and `iam:ListRoleTags` alongside tag/update actions when managing OIDC providers and roles with Terraform AWS provider v6+.
  - Linux/Digger provider lockfile checksums are present when CI/Digger installs providers on Linux.
- Prior blocking review threads are re-read and classified as resolved/stale against the current head and current plans before approving.

## Local validation fallback

When local Terraform is unavailable in the scheduled reviewer environment, still run lightweight checks and record the limitation:

```bash
git diff --check origin/<base>...HEAD
bash -n scripts/bootstrap-aws-production.sh scripts/bootstrap-github-actions-wif.sh
python3 -m json.tool scripts/state-bucket-lifecycle.json >/dev/null
```

Then rely on current hosted Digger/CI plan evidence for Terraform init/fmt/validate behavior. Do not approve Terraform/IAM bootstrap solely from source diff if hosted plan evidence is absent.

## Reporting shape

Separate code approval from process/merge state:

- `Verdict: Approve` when current plans/checks/trust boundaries/bootstrap docs are clean.
- `Merge readiness: approved from guardrail review; still blocked by process/merge-policy gates` when GitHub `mergeStateStatus` remains `BLOCKED` after approval.
- Note that material IAM/bootstrap changes still require human/operator sign-off; the guardrail approval is not a substitute for policy approval of bootstrap grants.
