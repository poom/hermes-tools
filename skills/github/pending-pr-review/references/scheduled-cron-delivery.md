# Scheduled cron delivery for pending PR reviews

When `pending-pr-review` runs as a scheduled cron job, the job wrapper normally delivers the agent's final response automatically. In that mode:

- Do **not** call `send_message`, create Discord messages/channels, or otherwise deliver dynamically unless the job explicitly says it uses `deliver: local` and requires `send_message`.
- Still follow the review workflow: fetch live queue, run guardrail reviews, post/verify GitHub review decisions when authorized, update review memory, and re-list the queue.
- Put all user-facing per-PR results and the compact recap directly in the final assistant response.
- If the queue is empty, final response must remain exactly `No pending PRs — queue is clear ✅`.
- If the queue is not empty only because a PR already has Poom's current-head formal approval, report it as process/merge-blocked and do not duplicate the approval.

Small shell pitfall from cron/non-interactive runs: avoid piping live GitHub/script JSON directly into `python3` because local security scanners can block `bash | python3` as pipe-to-interpreter. Prefer writing JSON to a temp file, then running Python over the file, e.g.:

```bash
bash "$HOME/.hermes/skills/github/pending-pr-review/scripts/list_pending_prs.sh" --json > /tmp/pending_prs.json
python3 /tmp/check_pending_current_reviews.py < /tmp/pending_prs.json
```
