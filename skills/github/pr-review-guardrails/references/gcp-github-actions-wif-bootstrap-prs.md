# GCP GitHub Actions WIF bootstrap PRs

Use this reference when a PR bootstraps or rewires central GitHub Actions Workload Identity Federation (WIF) for GCP, especially Terraform-managed pools/providers, CI service accounts, Digger workflows, and one-shot bootstrap scripts.

## Review posture

Treat these as security/IAM Terraform reviews, not ordinary scaffolding:

- Require a current Terraform/Digger plan for the affected project/root before approving. A local bootstrap/import note is not a substitute for plan evidence.
- Require human/policy approval for auth/permission changes. AI review can identify blockers and approve-level signals, but should not be the only approver for material IAM/WIF changes.
- Separate code correctness from merge/process readiness: GitGuardian or syntax checks passing does not clear missing policy-bot, Digger, or human-review gates.

## Evidence to gather

- PR metadata, current head SHA, checks, comments, review threads, and prior reviews.
- Digger project/root, backend config, var-file path, provider version, and workflow permissions.
- WIF provider attribute mappings and conditions (`assertion.repository_owner`, `assertion.sub`, `assertion.environment`, etc.).
- Service-account impersonation bindings (`roles/iam.workloadIdentityUser`) and the exact `principalSet`/`principal` used.
- Bootstrap script roles and resources, including project-level roles and state-bucket IAM.
- GitHub environment protection assumptions for any `repo:ORG/REPO:environment:production` subject.

## Common blockers

1. **No current plan output.** For central WIF/IAM resources, request changes until Digger routing is enabled and a current plan for the relevant project/root is posted and reviewed.
2. **Bootstrap grants not represented in Terraform.** If a bootstrap script grants durable roles such as `roles/iam.serviceAccountAdmin`, `roles/iam.workloadIdentityPoolAdmin`, or state-bucket `objectAdmin`/legacy roles, those privileges must either be modeled/imported into Terraform or documented as temporary bootstrap-only permissions with a clear lifecycle/removal path and human sign-off.
3. **Impersonation binding broader than the trust condition.** Prefer defense-in-depth: the `workloadIdentityUser` binding should match the intended subject/environment boundary where practical, not rely solely on a narrower provider condition while granting repository-wide impersonation.
4. **Unverified GitHub environment boundary.** If trust depends on `environment:production`, verify or explicitly require confirmation that the GitHub environment has appropriate protection rules.

## Approve-level signals

- Current Digger plan is available, reviewed, and matches the expected resource set/delta with no unexplained IAM drift or destructive changes.
- WIF provider condition and service-account impersonation binding align with the intended repositories/environments.
- Bootstrap-only privileges are either Terraform-managed, clearly temporary with a removal path, or justified in an ADR/ops note accepted by a human owner.
- Policy-bot/human review gates are clear or explicitly reported as remaining process blockers after a code-level approval.
- Local lightweight validation is clean where available (`git diff --check`, shell syntax, YAML parse), while unavailable local Terraform tooling is offset by CI/Digger evidence rather than ignored.

## Reporting guidance

When blocking, make the distinction explicit:

- The central WIF architecture may be sound.
- The merge is blocked because plan evidence, least-privilege/lifecycle documentation, and human/policy approval are missing.
- Do not label the PR as approved unless the formal GitHub review was actually posted and verified on the current head.
