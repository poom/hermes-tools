# deliver: local scheduled runs — use `hermes send` for Discord delivery

Use this when a scheduled `pending-pr-review` job is configured with `deliver: local` and the prompt explicitly requires dynamic user-visible Discord delivery.

## Lesson

In a cron/non-agent shell, importing `tools.send_message_tool` directly with the host `python3` can fail because it may not be the Hermes virtualenv Python (for example `No module named 'yaml'`). Do not build ad-hoc send-message wrappers around arbitrary Python unless you intentionally run the Hermes venv.

Prefer the CLI that already uses Hermes' configured environment and gateway credentials:

```bash
hermes send --to discord:<channel_id> --file /tmp/result.md --json
hermes send --to discord:<parent_channel_id> --file /tmp/index.md --json
```

This is appropriate only when the job's instructions say `deliver: local` / scheduler will not auto-post and user-facing per-PR results must be sent as the run progresses. In normal scheduled auto-delivery mode, do not call `hermes send` or `send_message`; put results in the final response.

## Verification

A successful Discord send returns JSON like:

```json
{
  "success": true,
  "platform": "discord",
  "chat_id": "1509201450851500203",
  "message_id": "1509201678019068136"
}
```

If sending to the parent/fallback channel, record the returned `message_id` in the local cutoff/final log when available.

## Pitfall

Do not interpret a host-Python import failure from a custom wrapper as a Discord or gateway outage. Retry once with `hermes send --to ... --file ... --json` before marking delivery failed.
