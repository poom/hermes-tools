# Discord daily threads for Hermes cron reminders

Use this pattern when a scheduled Hermes reminder should post into one Discord thread per day, named like `Reminder YYYY-MM-DD`, instead of repeatedly posting to the cron origin thread.

## Problem

`deliver: origin` sends the final cron response back to the original Discord conversation/thread. That is reliable, but it cannot dynamically choose a new thread per day. If the cron agent also calls `send_message` to the same origin, `send_message` may skip duplicate sends because cron auto-delivery will already post there.

## Pattern

1. Create a deterministic collector/helper script that runs at the beginning of the cron job.
2. The helper uses Discord REST API with `DISCORD_BOT_TOKEN` from `<home>/.hermes/.env` (never print the token):
   - `GET /channels/{parent_channel_id}` to get guild/channel metadata.
   - `GET /guilds/{guild_id}/threads/active` and find a thread with exact name `Reminder YYYY-MM-DD` and `parent_id == parent_channel_id`.
   - If not active, `GET /channels/{parent_channel_id}/threads/archived/public?limit=100` and find the same name.
   - If archived, `PATCH /channels/{thread_id}` with `{ "archived": false, "locked": false, "name": "Reminder YYYY-MM-DD" }`.
   - If missing, `POST /channels/{parent_channel_id}/threads` with `{ "name": "Reminder YYYY-MM-DD", "type": 11, "auto_archive_duration": 1440 }`.
3. Include the helper result in the collector output as e.g.:
   ```json
   {
     "discord_daily_thread": {
       "ok": true,
       "thread_id": "...",
       "thread_name": "Reminder 2026-05-13",
       "discord_target": "discord:<parent_channel_id>:<thread_id>"
     }
   }
   ```
4. Update the cron job to `deliver: local` and add `messaging` to `enabled_toolsets`.
5. In the cron prompt, instruct the agent to call:
   ```text
   send_message(action='send', target=<discord_daily_thread.discord_target>, message=<summary>)
   ```
   and make the final response a short local log only. This prevents duplicate posts to the origin.
6. Add a fallback target (usually the old origin thread) if thread creation or send fails.

## Notes and pitfalls

- `send_message` Discord targets support `discord:channel_id:thread_id`.
- For normal Discord public threads, send to the parent channel + thread ID target rather than changing cron `origin` dynamically.
- Keep link previews suppressed in reminder text by wrapping URLs in angle brackets (`<https://...>`) or omitting generic sign-in URLs.
- The helper must not persist or print secrets; it may load `.env` locally but should only output IDs/names/status/errors.
- This pattern depends on the bot having Discord permissions to create/manage public threads in the parent channel.
- Cron prompts are scanned both at create/update time and again after script output + skill content are assembled. If a collector injects untrusted email/chat/PR text, sanitize it before printing JSON: strip invisible Unicode (`U+200B`, `U+200C`, `U+200D`, `U+2060`, `U+FEFF`, bidi controls) and replace prompt-injection/exfiltration-looking snippets that match `tools/cronjob_tools.py::_CRON_THREAT_PATTERNS` (for example command-like `curl ... $TOKEN` text). Otherwise a reminder can silently fail with `last_status=error` and messages like `Blocked: prompt contains invisible unicode U+200C` or `Blocked: prompt matches threat pattern 'exfil_curl'`.
- If the job prompt says `deliver: local` + `send_message`, ensure the global cron hint does not contradict it. The historical hint said “do NOT use send_message”; either patch it to allow explicit deliver-local workflows or make the job `deliver: origin` and avoid dynamic thread routing. A contradictory hint can make the agent generate the reminder locally without actually posting it to Discord.
- To verify a missed reminder fix: run the collector script manually and scan stdout for `_CRON_THREAT_PATTERNS` + invisible chars; trigger the job with `hermes cron run <id>` or the cronjob tool; wait for completion; confirm `hermes cron list` shows `last_status: ok`; inspect `<home>/.hermes/sessions/session_cron_<id>_*.json` for the final assistant content or tool calls.
