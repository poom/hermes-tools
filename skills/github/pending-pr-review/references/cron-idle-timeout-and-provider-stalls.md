# Cron idle timeout and provider stalls

Session signal: a scheduled `pending-pr-review-hourly` run failed even though queue discovery and filtering scripts were healthy. The cron output ended with:

```text
TimeoutError: Cron job 'pending-pr-review-hourly' idle for 601s (limit 600s) — last activity: tool completed: read_file (0.8s)
```

Gateway error context showed a stale non-streaming model call before the idle timeout:

```text
Non-streaming API call stale for 300s (threshold 300s). model=gpt-5.5 ... Killing connection.
API call failed ... provider=openai-codex ... model=gpt-5.5 ... APIConnectionError
```

Durable lesson: when the pending-review cron fails with an idle timeout after the last successful tool call, do not assume the queue script or GitHub filter is broken. First distinguish:

1. **Queue discovery health** — run `scripts/test_list_pending_prs.sh` and `scripts/list_pending_prs.sh --stats-json`.
2. **Scheduler/process health** — check cron job status, latest output file, gateway status, and whether the job is actively executing.
3. **Model/provider stall** — inspect gateway error logs around the run time for stale non-streaming API calls, `APIConnectionError`, child/delegate timeouts, or no model progress after a tool call.
4. **Delivery context** — thread/channel delivery warnings can explain missing Discord output but are not necessarily the run failure.

Preferred mitigation for scheduled pending-review runs:

- Process fewer PRs per tick; one PR per scheduled run is safer than a large multi-PR batch when guardrail review uses multiple reviewers.
- Post/verify each PR immediately after its final head and duplicate-review checks, then move to the next PR.
- Avoid long non-streaming model calls inside cron when possible; use compact prompts/evidence packets and bounded reviewer lanes.
- If reviewer delegates stall, salvage in the parent with focused `gh` data and a direct compact Reviewer B prompt rather than waiting indefinitely.
- Emit an honest partial summary when timeout/retry risk is high: completed review IDs, current queue snapshot, and unfinished PRs.
- Increasing cron idle timeout is a last resort; it can hide stalled provider calls and delay reporting.

Do not encode the provider failure as a permanent claim that a provider or tool is broken. The reusable pattern is the diagnosis sequence and smaller-batch mitigation.
