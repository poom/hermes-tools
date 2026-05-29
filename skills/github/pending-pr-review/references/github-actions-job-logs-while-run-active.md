# Completed job logs while the workflow run is still active

Use this during scheduled pending-review drains when a live PR re-check shows a required workflow is still `in_progress`, but one matrix/job row has already completed as `failure` and the review needs enough evidence to classify the failure before deciding/posting.

## Symptom

`gh run view <run-id> --job <job-id> --log-failed` can return:

```text
run <run-id> is still in progress; logs will be available when it is complete
```

This can happen even when the particular failed job is complete and visible in `gh pr checks` / `gh run view --json jobs`.

## Fallback

Fetch the job log directly via the Actions job logs endpoint:

```bash
gh api -H 'Accept: application/vnd.github+json' \
  /repos/OWNER/REPO/actions/jobs/JOB_ID/logs \
  > /tmp/job-log.txt
```

If you need headers for diagnostics, write them to a saved file first; do not pipe the response directly into Python or another interpreter in Hermes.

## How to use the evidence

Inspect the failed test/linter/error text and classify it separately from the code-review verdict:

- Current-diff blocker: new/updated code or tests prove the PR is broken; request changes.
- Existing/flaky/environmental failure: report as process/merge-readiness, not as a code blocker.
- Workflow still active: say merge readiness depends on final CI even if the code review is approve-level.

Always cite the failed job name and the concrete log evidence in the review memory/final summary.
