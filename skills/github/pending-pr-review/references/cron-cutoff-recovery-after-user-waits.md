# Cron cutoff recovery when user is waiting for a specific pending-pr-review run

Use this when Poom asks for the result of a scheduled `pending-pr-review` run that has already ended, especially a run with `deliver: local` and `last_status=error`.

## Pattern

1. Identify the job/run:
   - `cronjob list` or `hermes cron list` for `pending-pr-review-hourly`.
   - Note `last_run_at`, `last_status`, `next_run_at`, and the newest output file under `~/.hermes/cron/output/<job-id>/`.
2. Read the newest output file near its end first. For failed deliver-local runs, the useful recovery summary is usually under `## Error`, not near the top (the top contains loaded skill text and prompt).
3. Classify each item in the recovery summary:
   - **Completed/verified**: formal GitHub review id exists and per-PR/user-facing report was sent. Do not duplicate.
   - **Verified GitHub review but delivery missing**: re-verify review id/head, then send the missing per-PR Discord result and parent index only.
   - **Draft body exists but GitHub action not posted**: re-fetch current head and live formal reviews. If head is unchanged and no current-head `poom` decision exists, submit the saved review body, verify via pulls reviews API, then send the per-PR Discord result and parent index.
   - **Evidence-only or reviewer-lanes-only**: do not post from stale evidence. Re-run or narrowly revalidate the guardrail review before posting.
4. After recovery, re-run the pending queue script and report the live remaining queue. Do not claim the queue is clear unless the script returns empty.

## Concrete recovery checks

For a drafted body recovery:

```bash
head=$(gh pr view OWNER/REPO#PR --json headRefOid --jq .headRefOid)
gh api repos/OWNER/REPO/pulls/PR/reviews --paginate > /tmp/reviews.json
python3 - <<'PY'
import json, sys
head = 'EXPECTED_HEAD'
rs = json.load(open('/tmp/reviews.json'))
existing = [r for r in rs if r.get('user',{}).get('login') == 'poom'
            and r.get('commit_id') == head
            and r.get('state') in ('APPROVED','CHANGES_REQUESTED')]
if existing:
    print('skip duplicate', existing[-1]['id'], existing[-1]['state'])
    sys.exit(3)
PY
```

Then post the saved full body (`gh pr review --approve/--request-changes --body-file ...`) and verify the new review id through `repos/OWNER/REPO/pulls/PR/reviews`, not just `gh pr view --json latestReviews`.

## Reporting shape

Keep the user update compact:

```text
<run time> run finished at <time>, but failed at tool-call cutoff.

Result from that run:
- Completed: <repo> #<n> — <verdict> — review id <id>
- Unfinished at cutoff: <repo> #<n> — <state>; no GitHub action posted before cutoff

Recovered now:
- <repo> #<n> — <action>
- Review id <id>
- PR channel: <discord URL>

Current pending queue after recovery: <count> PRs remain:
- ...
```

## Pitfalls

- `last_status=error` does not mean no useful work happened; the output file may contain verified GitHub actions and recoverable draft bodies.
- Do not use the cron final response as the only evidence for a formal review. Always verify current-head `poom` reviews via the pulls reviews API before posting or skipping.
- Do not carry over a drafted review if the PR head changed. Re-review/revalidate first.
- For `deliver: local`, a formal GitHub review can be posted but Discord delivery may still be missing; recover the missing per-PR message separately rather than duplicating the GitHub review.
