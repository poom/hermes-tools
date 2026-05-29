# EWA-Services/Tools #133 — PR velocity Chat config guardrail case

Session case for parent-delegated/no-posting review of `EWA-Services/Tools` PR #133, `feat: standardize PR velocity Chat config [ENG-964]`.

## Trigger

Use this as an example when reviewing PRs that standardize PR velocity / engineering-throughput Google Chat reports with Supabase cache/config defaults and optional SonarCloud enrichment, especially in parent-delegated mode where the reviewer must not post to GitHub or send platform messages.

## Reviewed state

- PR: `https://github.com/EWA-Services/Tools/pull/133`
- Head reviewed: `233712376f810985b59d810d0541b6514da62206`
- Base: `main` at `d4552bc4c0a10e8e5ce7a643917e48f89f0625c7`
- Final review decision: approve-level, report-only to parent.
- No GitHub reviews/comments or chat/platform messages were posted.

## Linear requirements that drove the review

- Public Chat report must be aggregate-only.
- Do not expose engineer names, individual rankings, watch callouts, or individual underperformance language.
- Include exact disclaimer: `PR counts and AI signals are throughput/context signals, not productivity ratings.`
- SonarCloud enrichment is non-blocking and should render `Sonar quality breakdown pending API ingestion` when unavailable/failing.
- Raw Sonar API responses and API errors should be stored for audit/debugging.
- Normal PR CI must not require Supabase, SonarCloud, GitHub org-wide, or Google Chat secrets.

## Checks that mattered

- Refreshed live PR metadata, review comments, formal reviews, issue comments, review threads, checks, base/head SHAs, and Linear context.
- Confirmed all prior review threads were resolved on the current head.
- Inspected config loading, committed JSON defaults, Chat renderer/tests, report orchestration, Supabase/cache/backend selection, Sonar pipeline/tests, workflow permissions/path filters, and docs.
- Local validation passed:
  - `git diff --check origin/main...HEAD`
  - `go test ./github`
  - `go vet ./github`
  - `go test ./...`
- Direct Claude CLI Reviewer B initially failed with `Error: Reached max turns (10)`; retrying with `--max-turns 20` completed and returned `APPROVE`.

## Resolved blocker patterns

- CLI/env/config ordering: committed `storage_backend: supabase` did not override explicit CLI or `STORAGE_BACKEND` selection.
- Chat date-window semantics: explicit `-current-from` / `-current-to` was rejected for Chat output where complete report weeks are required.
- Scan coverage: Chat collection covered trailing 12 weeks, not only the current display week.
- Storage validation scope: non-storage reports such as `counts` were not blocked by storage backend values.
- Sonar PR key attribution: pull request keys came from each raw PR number, avoiding one mapping value for all PRs.
- Malformed cached `raw_prs.merged_at`: errors surfaced instead of silently undercounting weekly Sonar aggregation.

## Process-gate classification

`policy-bot: main` failed with `.policy.yml` evaluation on `main`. Because this PR did not change the relevant policy file and local/CI code validations passed, the failure was reported as an external merge/process gate, not a code-review blocker.

## Parent-delegated output lesson

For no-posting parent-delegated reviews, the final response should separate actual side effects from proposed action:

- `github_action_performed: none (parent-delegated/no GitHub posting)`
- `github_action_proposed: APPROVE`
- exact `head_sha_reviewed`
- blockers/high-priority findings list
- non-blocking notes and process gates
- tests/checks run or inspected
- complete proposed formal GitHub review body for the parent to post after its own final head check

Avoid an unqualified `github_action: approved` unless a formal GitHub approval was actually posted.
