# Discord PR thread lifecycle

Context: A batch `pending-pr-review` run once mirrored the visible shape of `pr-review-guardrails` poorly: it emitted one top-level message per PR into the parent Discord channel, but did not create or rename dedicated PR threads. The user corrected this as a workflow issue.

Durable rule:

- Batch pending-PR output should follow the same Discord lifecycle as a single `pr-review-guardrails` review.
- One PR should get one dedicated Discord thread when possible.
- The thread starts as `<repo-name> #<pr-number> - Reviewing`.
- The thread is renamed to the final status, e.g. `<repo-name> #<pr-number> - Approved`, `Requested changes`, or `Commented`.
- The full per-PR result is posted inside that PR thread and includes the full PR URL.
- A parent-channel recap is optional and must not replace the per-PR thread result.

Implementation note:

- `send_message(target="discord:<parent_channel_id>:<thread_id>", ...)` can send to an existing Discord thread once the thread ID is known.
- `send_message(target="discord:#review-prs", ...)` alone is not sufficient in a normal Discord text channel; it produces parent-channel messages, not deterministic named/renamed PR review threads.
- Use `scripts/discord_pr_thread.py` for REST-based `create`, `send`, and `rename` when first-class Discord tooling is unavailable.
- Token inputs may be raw, `env:DISCORD_BOT_TOKEN`, or `@/path/to/file`, but logs and docs must never expose token values.

Fallback:

If thread creation or rename fails because of missing token or bot permissions, send separate parent-channel messages with full PR URLs and explicitly state that the thread/rename lifecycle could not be used.
