# Cron auto-delivery duplicate target skip

Use this when a scheduled `pending-pr-review` run is configured with a Discord/Telegram delivery target and the workflow also tries to send progress/debug messages to that exact same parent/fallback target.

## Symptom

`hermes send --to <cron-delivery-target> --file ... --json` can return success with a skip:

```json
{
  "success": true,
  "skipped": true,
  "reason": "cron_auto_delivery_duplicate_target",
  "target": "discord:<channel_id>",
  "note": "Skipped send_message to ... This cron job will already auto-deliver its final response to that same target..."
}
```

This is not a Discord failure and not proof that the progress line was posted. It is Hermes suppressing a likely duplicate to the same destination that will receive the final cron response.

## Handling

1. Still send per-PR results to a different PR-specific channel when available; those sends are not duplicates and should work normally.
2. Preserve any skipped parent progress/debug lines in durable run files and include the important ones in the final cron response recap, because the final response is what the scheduler will auto-post to the parent/fallback target.
3. In the final recap, mention that parent progress sends to the auto-delivery target were skipped by `cron_auto_delivery_duplicate_target` so Poom knows why intermediate parent debug messages may be absent.
4. Do not retry the same `hermes send --to <same-parent-target>` in a loop; it will continue to be skipped. Use a distinct target only if the job explicitly authorizes one.
5. Treat this separately from per-PR channel delivery failures. A skipped parent duplicate does not mean the per-PR channel message failed.

## Reporting shape

When this happens after a completed PR, the final response should include compact parent-progress equivalents, for example:

```text
Parent progress messages to discord:<parent_id> were attempted, but `hermes send` skipped them as `cron_auto_delivery_duplicate_target`; this final response is the parent/fallback recap. The per-PR Discord channel message was sent successfully.
```
