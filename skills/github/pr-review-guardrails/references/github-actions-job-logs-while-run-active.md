# GitHub Actions job logs while a workflow run is still active

Use this when a required workflow is still `in_progress` but one matrix/job row is already `failure` and you need enough evidence to classify it before the full run completes.

## Problem

`gh run view <run-id> --job <job-id> --log-failed` can refuse to return logs while the overall workflow run is still active:

```text
run <run-id> is still in progress; logs will be available when it is complete
```

This can happen even when the specific job has already completed and is shown as failed in `gh pr checks` / `gh run view --json jobs`.

## Reliable fallback

Fetch the completed job log directly through the Actions job logs API:

```bash
gh api -H 'Accept: application/vnd.github+json' \
  /repos/OWNER/REPO/actions/jobs/JOB_ID/logs \
  > /tmp/job-log.txt
```

Notes:
- The endpoint may return plain text with HTTP headers if `--include` is used; either omit `--include` or strip headers before analysis.
- Do not pipe the API response directly into Python or another interpreter in Hermes. Save to `/tmp/*.txt` first, then inspect/search the file.
- This is especially useful for matrix workflows: one failed lane can be inspected while sibling lanes are still `in_progress`.

## Review classification guidance

Use the fetched log to distinguish:
- a current-diff/code blocker introduced by the PR;
- an existing flaky/environmental test failure;
- a process/merge-readiness gate that should be reported but not treated as a code-review blocker.

In the review body, cite the failed job name, the specific failing test/error, and whether it affects the current diff. If the workflow remains active, say that the workflow is not fully green yet and merge readiness still depends on final CI/process gates.
