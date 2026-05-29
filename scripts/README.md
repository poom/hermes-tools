# Scripts

Portable Hermes cron/helper scripts shared between machines. Scripts should not contain personal absolute home-directory paths; use env vars or CLI flags instead.

## Shared helper module

`hermes_tools_common.py` provides:

- `hermes_home()` - `$HERMES_HOME` or `~/.hermes`.
- `hermes_scripts_dir()` - `$HERMES_SCRIPTS_DIR` or `$HERMES_HOME/scripts`.
- `load_hermes_dotenv()` - dependency-free dotenv loader for `$HERMES_ENV_FILE` or `$HERMES_HOME/.env`.
- `portable_env()` - PATH with `$HERMES_EXTRA_PATHS`, `~/.local/bin`, `~/.bun/bin`, Homebrew, and `/usr/local/bin` when present.
- `which_executable()` - env/PATH executable resolver.

## Script inventory

- `codex_daily_usage_record.py` - local Codex/ChatGPT CLI token usage recorder.
  - Optional env: `CODEX_SESSIONS_DIR`, `CODEX_USAGE_OUT_DIR`, `CODEX_USAGE_MACHINE_ID`, `BUNX`.
- `discord_daily_reminder_thread.py` - find/create a Discord daily reminder thread.
  - Required: `DISCORD_BOT_TOKEN`, plus `--channel-id` or `DISCORD_REMINDER_CHANNEL_ID`.
  - Optional: `HERMES_TOOLS_TIMEZONE`, `--prefix`, `--date`.
- `discord_pr_channel_closer.py` - delete `review-prs` text channels after linked GitHub PRs are closed/merged.
  - Required: `DISCORD_BOT_TOKEN`, and `--guild-id` or `DISCORD_PR_REVIEW_GUILD_ID`/`DISCORD_GUILD_ID`.
  - Optional: `DISCORD_PR_REVIEW_CATEGORY_ID`, `DISCORD_PR_REVIEW_CATEGORY_NAME`, `DISCORD_PR_REVIEW_MAX_MESSAGES`.
  - Requires `gh` authenticated for PR status checks.
- `discord_pr_thread_closer.py` - archive active Discord PR review threads after linked GitHub PRs are closed/merged.
  - Required: `DISCORD_BOT_TOKEN`, and `--channel-id` or `DISCORD_PR_THREAD_PARENT_CHANNEL_ID`.
  - Requires `gh` authenticated.
- `hermes_config_backup_sync.py` - backup safe Hermes config/customizations into a git checkout.
  - Optional env: `HERMES_CONFIG_BACKUP_DIR`, `HERMES_CONFIG_BACKUP_REMOTE`, `HERMES_CONFIG_BACKUP_REPO_LABEL`, `HERMES_CONFIG_BACKUP_BRANCH`.
  - Uses rebase (`git pull --rebase --autostash`) when pulling a configured remote branch.
- `monitor_github_pr.py` - generic quiet GitHub PR monitor that can schedule a Hermes re-review job when the head SHA changes.
  - Required: `--pr-url` or `GITHUB_PR_MONITOR_URL`.
  - Optional env/flags: `GITHUB_PR_MONITOR_REPO`, `GITHUB_PR_MONITOR_NUMBER`, `GITHUB_PR_MONITOR_REPO_DIR`, `GITHUB_PR_MONITOR_STATE_FILE`, `GITHUB_PR_MONITOR_REVIEW_NOTE`, `GITHUB_PR_MONITOR_LOCK_FILE`, `HERMES_CLI`, `GITHUB_PR_MONITOR_DELIVER`, `GITHUB_PR_MONITOR_SKILLS`, `GITHUB_PR_MONITOR_REVIEW_INSTRUCTION`, `GITHUB_PR_MONITOR_INITIALIZE_ONLY`, `GITHUB_PR_MONITOR_NO_SCHEDULE_REVIEW`.
  - Requires `gh`, `git`, and Hermes CLI when scheduling reviews.
- `monitor_lss_pr201.py` - backward-compatible wrapper around `monitor_github_pr.py`; configure it the same way.
- `personal_pr_monitor_collect.py` - read-only collector for open authored GitHub PRs.
  - Optional env: `HERMES_TOOLS_TIMEZONE`.
  - Requires `gh` authenticated.
- `personal_triage_collect.py` - read-only collector for unread Gmail and Google Chat triage data.
  - Optional env: `GOG_ACCOUNTS` (comma-separated, default `work,personal`), `POKE_CLI`, `HERMES_TOOLS_TIMEZONE`.
  - Requires `gog`; Google Chat collection requires `poke`.
- `restart_gateway_when_idle.py` - macOS launchd helper to restart Hermes gateway after idle.
  - Optional env: `HERMES_GATEWAY_LAUNCHD_LABEL`.

## Cron examples

```bash
# Discord daily reminder thread helper
DISCORD_REMINDER_CHANNEL_ID=123456789 \
  "$HERMES_HOME/scripts/discord_daily_reminder_thread.py"

# GitHub PR monitor in no-agent cron mode
GITHUB_PR_MONITOR_URL=https://github.com/OWNER/REPO/pull/123 \
GITHUB_PR_MONITOR_DELIVER=discord:CHANNEL_OR_THREAD_ID \
  "$HERMES_HOME/scripts/monitor_github_pr.py"
```

Keep per-machine IDs, tokens, and delivery targets in that machine's environment or `$HERMES_HOME/.env`.
