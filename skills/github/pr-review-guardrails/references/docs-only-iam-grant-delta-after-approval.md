# Docs-only IAM grant delta after prior approval

Use this when a PR already had a full guardrail approval on an older head and the current head adds only documentation about manual IAM grants / rollout permissions.

Concrete session pattern: EWA-Services/Tools #137. Poom had approved head `5fde2c0...`; current head `6d886b5...` added only 12 README lines documenting manual grants for the Claude BigQuery MCP connector.

## Review workflow

1. Verify the prior full approval against the old head through the pulls reviews API; do not rely only on `reviewDecision`.
2. Verify the current-head delta is documentation-only:
   ```bash
   git diff --name-status OLD_APPROVED_HEAD..HEAD
   git diff --stat OLD_APPROVED_HEAD..HEAD
   git diff --unified=80 OLD_APPROVED_HEAD..HEAD -- <docs path>
   ```
3. Cross-check the documented grants against actual runtime/deploy code:
   - Billing/job-creation project used by scripts and API calls (for example `BIGQUERY_BILLING_PROJECT`, `/projects/{project}/jobs`, `/projects/{project}/queries`).
   - Durable state backend and project/database/collection env vars (for example Firestore replay-state paths).
   - Data-access scope in config/catalog (for example `toolbox.yaml` `allowedDatasets`, static approved catalog, query guardrails).
4. Validate least-privilege wording explicitly:
   - Positive grants match runtime needs (for example `roles/bigquery.jobUser` for job creation, `roles/datastore.user` for Firestore document create/read/update).
   - Data grants are scoped to reviewed datasets/views only.
   - Docs explicitly avoid data editor/owner/broad project-level read access for queryable data.
5. Run cheap validation even for docs-only deltas:
   ```bash
   git diff --check origin/<base>...HEAD
   git diff --check OLD_APPROVED_HEAD..HEAD
   bash -n path/to/deploy.sh path/to/entrypoint.sh  # when docs reference scripts/envs
   ```
6. Re-read live review threads and comments. Prior code/security blockers can be considered resolved/stale only after author replies plus current-code evidence support that conclusion.
7. Run compact Reviewer B over the delta evidence. Ask whether the docs-only IAM delta creates a request-changes-level risk.
8. Final head recheck before returning/posting.

## Decision guidance

Approve-level when:
- The post-approval delta is docs-only.
- The documented IAM grants match the already-reviewed deploy/runtime paths.
- The wording preserves least privilege and does not instruct broad data access.
- Prior blocker threads are resolved/stale and no new thread targets the delta.

Treat as process notes, not docs blockers:
- Current-head `finn-ai-coder / review` / metadata refresh failures caused by missing current-head AI metadata after a docs-only push (`failure (none)`).
- Pending Policy Bot approval when the code/docs review itself is approve-level.
- Commit signature `unknown_key`, unless the user explicitly asks to enforce signed-commit policy as a blocker.

## Proposed review-body language

Mention that the old-approved-head to current-head delta is documentation-only, then summarize the grant/runtime alignment:

- `roles/bigquery.jobUser` matches BigQuery job creation in the billing project.
- `roles/datastore.user` matches Firestore-backed OAuth replay-state documents.
- Read-only dataset/view grants are limited to reviewed config/catalog entries and explicitly exclude editor/owner/broad project-level access.
