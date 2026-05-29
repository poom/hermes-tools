# Discord PR channel cleanup cron

Session-derived pattern for adding a destructive but safe scheduled job that deletes Discord `review-prs` text channels after their GitHub PR is closed or merged. Keep this as a class-level operational recipe; adapt IDs/names per install.

## Use case

The install already had a `discord_pr_thread_closer.py` no-agent job that archives active PR review threads under a parent channel. The missing class was text-channel cleanup: scan text channels inside the Discord `review-prs` category, extract the canonical GitHub PR URL from each channel, verify the PR is closed/merged, then delete the channel.

When asked to add this, keep the existing thread closer unless the user explicitly asks to replace it. Thread closer and channel closer are complementary.

## Script shape

Place a deterministic script in `$HERMES_HOME/scripts/discord_pr_channel_closer.py`.

Key implementation points:

- Load `.env` for `DISCORD_BOT_TOKEN`; do not print secrets.
- Default guild can be the user's Hermes Mac Discord guild, but allow overrides:
  - `DISCORD_PR_REVIEW_GUILD_ID` or `DISCORD_GUILD_ID`
  - `DISCORD_PR_REVIEW_CATEGORY_ID`
  - `DISCORD_PR_REVIEW_CATEGORY_NAME` defaulting to `review-prs`
  - `DISCORD_PR_REVIEW_MAX_MESSAGES` defaulting to a finite scan cap such as `500`
- Resolve the category via Discord REST `GET /guilds/{guild_id}/channels` and require a single category match if no category id is set.
- Only consider Discord channel type `0` (`GUILD_TEXT`) whose `parent_id` is the resolved category id.
- Extract GitHub PR URLs with a canonical regex like:
  - `https?://github.com/<owner>/<repo>/pull/<number>`
- Prefer channel topic/name before paging messages. Then page recent messages (`GET /channels/{id}/messages?limit=...`) and inspect message content, embed URL/title/description/fields, and attachment URLs.
- For every candidate, verify status via GitHub before any destructive action:
  - `gh api repos/{owner}/{repo}/pulls/{number} --jq '{state:.state, merged:.merged, merged_at:.merged_at, closed_at:.closed_at, title:.title, html_url:.html_url}'`
  - only act when `state` is `closed` or `merged` is true.
- Delete with Discord REST `DELETE /channels/{channel_id}` only after all checks pass.
- Store a small last-run record under `$HERMES_HOME/state/discord_pr_channel_closer_state.json` for auditability.

## CLI flags and output contract

Support:

- `--dry-run` — never delete; still list candidates.
- `--json` — always print full JSON summary, including checked channel count, candidates, skipped channels if verbose, and errors.
- `--verbose` — include skipped channels/errors in human output.

No-agent cron stdout contract:

- default no-op: print nothing;
- deletion run: print one plain line per channel, e.g. `<channel-name> - deleted`;
- dry-run deletion candidates: `<channel-name> - would delete`;
- hard errors: `ERROR: <channel-name>: <message>`.

This matches the user's preferred Discord closer summary format and avoids noisy scheduled reminders.

## Verification sequence

1. Make the script executable and run a destructive-safety dry-run:
   - `$HERMES_HOME/scripts/discord_pr_channel_closer.py --dry-run --json`
2. Inspect:
   - resolved guild/category id/name;
   - checked channel count;
   - deletion candidate list;
   - zero unexpected errors.
3. Create the no-agent cron job:
   - name: `Discord PR channel closer (review-prs category)`
   - schedule: `every 60m`
   - script: `discord_pr_channel_closer.py`
   - `no_agent: true`
   - deliver: usually `origin` or a specific Discord channel if the user wants cleanup reports elsewhere.
4. Run the script once manually if the user requested immediate cleanup.
5. Run a second dry-run JSON verification; expected result after cleanup is no deletion candidates and no errors.
6. List cron jobs and confirm both jobs remain enabled when applicable:
   - existing `discord_pr_thread_closer.py` thread closer;
   - new `discord_pr_channel_closer.py` channel closer.

## Pitfalls

- Do not rely on channel names alone; require an extracted GitHub PR URL unless the user explicitly defines a safe naming-to-repo map.
- Do not delete archived threads here; text-channel cleanup and thread archiving are separate scripts/jobs.
- Do not create duplicate cron jobs if a channel closer already exists; update or enable the existing one.
- Do not deliver noisy no-op cron output. In no-agent mode, empty stdout is the right no-op signal.
- Do not remove the existing thread closer when adding the text-channel closer unless explicitly instructed.
