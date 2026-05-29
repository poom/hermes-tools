# Preserved Hermes Agent Guide

This reference preserves the previous detailed operating guide. Use it for step-by-step procedures after the lean `SKILL.md` routes to this skill.

## Previous Frontmatter

```yaml
name: hermes-agent
description: "Configure, extend, or contribute to Hermes Agent."
version: 2.0.0
author: Hermes Agent + Teknium
license: MIT
metadata:
  hermes:
    tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, development]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [claude-code, codex, opencode]
```

## Previous Operating Guide

# Hermes Agent

Hermes Agent is an open-source AI agent framework by Nous Research that runs in your terminal, messaging platforms, and IDEs. It belongs to the same category as Claude Code (Anthropic), Codex (OpenAI), and OpenClaw — autonomous coding and task-execution agents that use tool calling to interact with your system. Hermes works with any LLM provider (OpenRouter, Anthropic, OpenAI, DeepSeek, local models, and 15+ others) and runs on Linux, macOS, and WSL.

What makes Hermes different:

- **Self-improving through skills** — Hermes learns from experience by saving reusable procedures as skills. When it solves a complex problem, discovers a workflow, or gets corrected, it can persist that knowledge as a skill document that loads into future sessions. Skills accumulate over time, making the agent better at your specific tasks and environment.
- **Persistent memory across sessions** — remembers who you are, your preferences, environment details, and lessons learned. Pluggable memory backends (built-in, Honcho, Mem0, and more) let you choose how memory works.
- **Multi-platform gateway** — the same agent runs on Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email, and 10+ other platforms with full tool access, not just chat.
- **Provider-agnostic** — swap models and providers mid-workflow without changing anything else. Credential pools rotate across multiple API keys automatically.
- **Profiles** — run multiple independent Hermes instances with isolated configs, sessions, skills, and memory.
- **Extensible** — plugins, MCP servers, custom tools, webhook triggers, cron scheduling, and the full Python ecosystem.

People use Hermes for software development, research, system administration, data analysis, content creation, home automation, and anything else that benefits from an AI agent with persistent context and full system access.

**This skill helps you work with Hermes Agent effectively** — setting it up, configuring features, spawning additional agent instances, troubleshooting issues, finding the right commands and settings, and understanding how the system works when you need to extend or contribute to it.

**Docs:** https://hermes-agent.nousresearch.com/docs/

## Quick Start

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Interactive chat (default)
hermes

# Single query
hermes chat -q "What is the capital of France?"

# Setup wizard
hermes setup

```

Continuation:

```bash
# Change model/provider
hermes model

# Check health
hermes doctor
```

---

## CLI Reference

### Global Flags

```
hermes [flags] [command]

  --version, -V             Show version
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --pass-session-id         Include session ID in system prompt
```

No subcommand defaults to `chat`.

### Chat

```
hermes chat [flags]
  -q, --query TEXT          Single query, non-interactive
  -m, --model MODEL         Model (e.g. anthropic/claude-sonnet-4)
  -t, --toolsets LIST       Comma-separated toolsets
  --provider PROVIDER       Force provider (openrouter, anthropic, nous, etc.)
  -v, --verbose             Verbose output
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --source TAG              Session source tag (default: cli)
```

### Configuration

```
hermes setup [section]      Interactive wizard (model|terminal|gateway|tools|agent)
hermes model                Interactive model/provider picker
hermes config               View current config
hermes config edit          Open config.yaml in $EDITOR
hermes config set KEY VAL   Set a config value
hermes config path          Print config.yaml path
hermes config env-path      Print .env path
hermes config check         Check for missing/outdated config
hermes config migrate       Update config with new options
hermes login [--provider P] OAuth login (nous, openai-codex)
hermes logout               Clear stored auth
hermes doctor [--fix]       Check dependencies and config
```

Continuation:

```
hermes status [--all]       Show component status
```

### Tools & Skills

```
hermes tools                Interactive tool enable/disable (curses UI)
hermes tools list           Show all tools and status
hermes tools enable NAME    Enable a toolset
hermes tools disable NAME   Disable a toolset

hermes skills list          List installed skills
hermes skills search QUERY  Search the skills hub
hermes skills install ID    Install a skill (ID can be a hub identifier OR a direct https://…/SKILL.md URL; pass --name to override when frontmatter has no name)
hermes skills inspect ID    Preview without installing
hermes skills config        Enable/disable skills per platform
hermes skills check         Check for updates
hermes skills update        Update outdated skills
```

Continuation:

```
hermes skills uninstall N   Remove a hub skill
hermes skills publish PATH  Publish to registry
hermes skills browse        Browse all available skills
hermes skills tap add REPO  Add a GitHub repo as skill source
```

When replacing a skill from a GitHub repository directory URL (for example `https://github.com/ORG/REPO/tree/main/skills/name`), do not pass the tree URL directly to `hermes skills install`; the installer only accepts hub IDs or direct HTTP(S) URLs to a `SKILL.md` file. First try the raw URL (`https://raw.githubusercontent.com/ORG/REPO/main/skills/name/SKILL.md`). If raw `SKILL.md` 404s or the skill has companion files (`references/`, `scripts/`, evals, `agents/`), clone the repo, uninstall the existing skill (`printf 'y\n' | hermes skills uninstall name` because uninstall prompts), then copy the whole skill directory into `$HERMES_HOME/skills/<category>/<name>`. Verify with `hermes skills list | grep -i name`, `skill_view(name)`, and any bundled checker/test script.

### MCP Servers

```
hermes mcp serve            Run Hermes as an MCP server
hermes mcp add NAME         Add an MCP server (--url or --command)
hermes mcp remove NAME      Remove an MCP server
hermes mcp list             List configured servers
hermes mcp test NAME        Test connection
hermes mcp configure NAME   Toggle tool selection
```

### Gateway (Messaging Platforms)

```
hermes gateway run          Start gateway foreground
hermes gateway install      Install as background service
hermes gateway start/stop   Control the service
hermes gateway restart      Restart the service
hermes gateway status       Check status
hermes gateway setup        Configure platforms
```

Supported platforms: Telegram, Discord, Slack, WhatsApp, Signal, Email, SMS, Matrix, Mattermost, Home Assistant, DingTalk, Feishu, WeCom, BlueBubbles (iMessage), Weixin (WeChat), API Server, Webhooks. Open WebUI connects via the API Server adapter.

Platform docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

### Sessions

```
hermes sessions list        List recent sessions
hermes sessions browse      Interactive picker
hermes sessions export OUT  Export to JSONL
hermes sessions rename ID T Rename a session
hermes sessions delete ID   Delete a session
hermes sessions prune       Clean up old sessions (--older-than N days)
hermes sessions stats       Session store statistics
```

### Cron Jobs

```
hermes cron list            List jobs (--all for disabled)
hermes cron create SCHED    Create: '30m', 'every 2h', '0 9 * * *'
hermes cron edit ID         Edit schedule, prompt, delivery
hermes cron pause/resume ID Control job state
hermes cron run ID          Trigger on next tick
hermes cron remove ID       Delete a job
hermes cron status          Scheduler status
```

Quick status triage for “is cron/job X running?”:
1. Run `hermes cron list` (or the cronjob list tool) and identify the job by name/skill/id; report `enabled`, `state`, `last_run_at`, `last_status`, `last_delivery_error`, `next_run_at`, and delivery target.
2. Run `hermes cron status` to verify the gateway scheduler is actually alive; include the gateway PID and next global run if relevant.
3. Check whether the specific job is actively executing before saying it is “running now”: `ps aux | grep -E '<job-id>|<job-name>|hermes chat|cron' | grep -v grep` and/or inspect the latest `<home>/.hermes/cron/.tick.lock` timestamp. Distinguish “scheduled/enabled” from “currently executing.”
4. If an interval job appears to have a “2 hour” gap (for example `last_run_at=14:22` but `next_run_at=16:22` on an hourly job), check for an in-progress run and newest output file before assuming the schedule is wrong. The scheduler calls `advance_next_run()` before execution for at-most-once semantics, so `next_run_at` may move forward while `last_run_at` still shows the previous completed run. After the run finishes, `mark_job_run()` updates `last_run_at` and recomputes `next_run_at` from completion time; explain this as “hourly, but anchored to execution/completion time, and the UI is misleading during active runs.”
5. For the latest result, inspect `<home>/.hermes/cron/output/<job-id>/` newest markdown file and, if needed, `<home>/.hermes/logs/gateway.error.log` around the latest run. Beware cron runs that produce useful output but are logged as errors because the scheduler wrapped non-empty response text as a `RuntimeError`; compare `hermes cron list` `last_status` with output/log details before summarizing.

When a scheduled task needs fresh system data, prefer a small deterministic collector script plus a prompt that analyzes the script stdout. With the cronjob tool this means `script: "name.py"` pointing at `<home>/.hermes/scripts/name.py`, and `enabled_toolsets` limited to what the run needs (for example `terminal,file` for read-only triage, add `delegation` only for auto-fix jobs). Keep collector output compact: truncate bodies/comments, cap item counts, and include operational stderr separately so the agent can report tool issues without flooding the message. For nonstandard times like 08:00/12:30/17:00, create separate cron schedules if the cron expression would otherwise be awkward (e.g. `0 8,17 * * *` plus `30 12 * * *`).

For deterministic maintenance jobs that do not need an LLM (for example, closing Discord PR review threads once the GitHub PR is closed/merged), create a script under `<home>/.hermes/scripts/`, set `no_agent: true`, and make the script quiet on no-op runs but print compact JSON when it takes action or errors. Use `hermes cron create 'every 1h'`/cronjob with `schedule: "every 1h"` and `script: "name.py"`; after creation, update delivery if needed with a comma-separated list such as `deliver: "origin,discord:<channel_id>"` so results are posted both to the requesting thread and the monitored channel. Verify with a dry-run first, run once manually if cleanup is immediately desired, then confirm `hermes cron list` shows the intended `deliver`, `schedule`, `script`, and `no_agent` fields.

For Discord reminders that should use one thread per day (for example `Reminder YYYY-MM-DD`), do not rely on `deliver: origin`, because it always posts back to the original thread. Instead, have the collector/helper create or find the daily thread via Discord REST, emit a `discord_target` like `discord:<parent_channel_id>:<thread_id>`, set the cron job to `deliver: local`, enable the `messaging` toolset, and have the cron prompt call `send_message` to that dynamic target. Keep a fallback target for failures. Cron scans the fully assembled prompt (including script output and skill content), so sanitize untrusted collector output for invisible Unicode and command-like injection/exfiltration strings before printing it; otherwise the job can fail with `Blocked: prompt contains invisible unicode U+200C` or `_CRON_THREAT_PATTERNS` hits. Also ensure the global cron execution hint does not contradict deliver-local jobs by forbidding `send_message`. See `references/discord-daily-cron-threads.md` for the full recipe, scanner pitfalls, and verification steps.

### Webhooks

```
hermes webhook subscribe N  Create route at /webhooks/<name>
hermes webhook list         List subscriptions
hermes webhook remove NAME  Remove a subscription
hermes webhook test NAME    Send a test POST
```

### Profiles

```
hermes profile list         List all profiles
hermes profile create NAME  Create (--clone, --clone-all, --clone-from)
hermes profile use NAME     Set sticky default
hermes profile delete NAME  Delete a profile
hermes profile show NAME    Show details
hermes profile alias NAME   Manage wrapper scripts
hermes profile rename A B   Rename a profile
hermes profile export NAME  Export to tar.gz
hermes profile import FILE  Import from archive
```

### Credential Pools

```
hermes auth add             Interactive credential wizard
hermes auth list [PROVIDER] List pooled credentials
hermes auth remove P INDEX  Remove by provider + index
hermes auth reset PROVIDER  Clear exhaustion status
```

### Other
### Other (2)
```
hermes insights [--days N]  Usage analytics
hermes update               Update to latest version
hermes pairing list/approve/revoke  DM authorization
hermes plugins list/install/remove  Plugin management
hermes honcho setup/status  Honcho memory integration (requires honcho plugin)
hermes memory setup/status/off  Memory provider config
hermes completion bash|zsh  Shell completions
hermes acp                  ACP server (IDE integration)
hermes claw migrate         Migrate from OpenClaw
hermes uninstall            Uninstall Hermes
```

#### Token Usage / Insights Quick Recipe

When the user asks about ChatGPT subscription / Codex token usage, distinguish it from Hermes' own session DB and OpenAI API billing. Codex token usage can be reconstructed from local `<home>/.codex/sessions/**/*.jsonl` logs by aggregating `payload.info.total_token_usage`; this is machine-local, so daily records must include a machine ID and need one recorder per machine for account-wide totals. See `references/codex-subscription-usage-recording.md` for the daily recorder pattern, no-agent cron setup, multi-machine pitfall, and auth notes.

When the user asks for Hermes token totals (today, 7D, all-time, average since first use):

1. Start with the supported CLI summaries:
   ```bash
   hermes insights --days 1
   hermes insights --days 7
   hermes insights --days 9999
   ```
2. For precise calendar-day or all-time averages, query the session DB directly. Hermes stores sessions in `<home>/.hermes/state.db` (profile-aware installs may use a different `$HERMES_HOME`). The `hermes insights` “Total tokens” formula is:
   ```text
   input_tokens + output_tokens + cache_read_tokens + cache_write_tokens
   ```
   It intentionally does **not** include `reasoning_tokens`.
3. Useful SQLite query:
   ```bash
   sqlite3 -header -column <home>/.hermes/state.db <<'SQL'
   WITH s AS (
     SELECT date(started_at,'unixepoch','localtime') AS day,
            started_at,
            input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
            (input_tokens+output_tokens+cache_read_tokens+cache_write_tokens) AS total_tokens
     FROM sessions
   )
   SELECT 'all_time' period, SUM(total_tokens) total, MIN(day) first_day, MAX(day) last_day,
          COUNT(DISTINCT day) active_days,
          ROUND(SUM(total_tokens)*1.0/COUNT(DISTINCT day)) avg_tokens_per_active_day
   FROM s
   UNION ALL
   SELECT 'today_calendar', SUM(total_tokens), MIN(day), MAX(day), COUNT(DISTINCT day), SUM(total_tokens)
   FROM s WHERE day=date('now','localtime')
   UNION ALL
   SELECT 'rolling_7d', SUM(total_tokens), MIN(day), MAX(day), COUNT(DISTINCT day), ROUND(SUM(total_tokens)*1.0/7.0)
   FROM s WHERE started_at >= strftime('%s','now','-7 days')
   UNION ALL
   SELECT 'last_7_calendar_days', SUM(total_tokens), MIN(day), MAX(day), COUNT(DISTINCT day), ROUND(SUM(total_tokens)*1.0/7.0)
   FROM s WHERE day >= date('now','localtime','-6 days') AND day <= date('now','localtime');
   SQL
   ```
4. In the final answer, label whether “7D” means rolling last 7×24h or last 7 calendar days if both could be relevant. Prefer a compact table.

---

## Slash Commands (In-Session)

Type these during an interactive chat session.

### Session Control
```
/new (/reset)        Fresh session
/clear               Clear screen + new session (CLI)
/retry               Resend last message
/undo                Remove last exchange
/title [name]        Name the session
/compress            Manually compress context
/stop                Kill background processes
/rollback [N]        Restore filesystem checkpoint
/background <prompt> Run prompt in background
/queue <prompt>      Queue for next turn
/resume [name]       Resume a named session
```

### Configuration (2)
```
/config              Show config (CLI)
/model [name]        Show or change model
/personality [name]  Set personality
/reasoning [level]   Set reasoning (none|minimal|low|medium|high|xhigh|show|hide)
/verbose             Cycle: off → new → all → verbose
/voice [on|off|tts]  Voice mode
/yolo                Toggle approval bypass
/skin [name]         Change theme (CLI)
/statusbar           Toggle status bar (CLI)
```

### Tools & Skills (2)
```
/tools               Manage tools (CLI)
/toolsets            List toolsets (CLI)
/skills              Search/install skills (CLI)
/skill <name>        Load a skill into session
/cron                Manage cron jobs (CLI)
/reload-mcp          Reload MCP servers
/plugins             List plugins (CLI)
```

### Gateway
```
/approve             Approve a pending command (gateway)
/deny                Deny a pending command (gateway)
/restart             Restart gateway (gateway)
/sethome             Set current chat as home channel (gateway)
/update              Update Hermes to latest (gateway)
/platforms (/gateway) Show platform connection status (gateway)
```

### Utility
```
/branch (/fork)      Branch the current session
/fast                Toggle priority/fast processing
/browser             Open CDP browser connection
/history             Show conversation history (CLI)
/save                Save conversation to file (CLI)
/paste               Attach clipboard image (CLI)
/image               Attach local image file (CLI)
```

### Info
```
/help                Show commands
/commands [page]     Browse all commands (gateway)
/usage               Token usage
/insights [days]     Usage analytics
/status              Session info (gateway)
/profile             Active profile info
```

### Exit
```
/quit (/exit, /q)    Exit CLI
```

---

## Key Paths & Config

```
<home>/.hermes/config.yaml       Main configuration
<home>/.hermes/.env              API keys and secrets
$HERMES_HOME/skills/        Installed skills
<home>/.hermes/sessions/         Session transcripts
<home>/.hermes/logs/             Gateway and error logs
<home>/.hermes/auth.json         OAuth tokens and credential pools
<home>/.hermes/hermes-agent/     Source code (if git-installed)
```

Profiles use `<home>/.hermes/profiles/<name>/` with the same layout.

### Config Sections

Edit with `hermes config edit` or `hermes config set section.key value`.

### Backing Up Hermes Config to Git

When the user asks to back up Hermes configuration to a private Git/GitHub repo, include durable customizations but never commit raw secrets or runtime state:

1. Use `hermes config path` and `hermes config env-path` to confirm source files. Treat `.env`, `auth.json`, OAuth tokens, credential pools, and state DBs as secrets/state that must stay ignored.
2. If backing up `config.yaml`, scan it for literal `api_key`, token, secret, password, or credential fields. If literal values are present, commit a redacted copy (for example replacing literal `api_key:` values with `REDACTED_COMMIT_SAFE`) rather than the raw file.
3. Include useful portable configuration/customization files such as `config.yaml` (redacted), `SOUL.md`, `skills/`, `scripts/`, `hooks/`, `bin/` if text-safe, and `cron/jobs.json` when scripts/jobs are part of the setup.
4. Exclude Hermes runtime/generated data with `.gitignore`: `.env`, `auth.json`, `state.db*`, `kanban.db*`, `sessions/`, `message-sessions/`, `logs/`, `cache/`, `audio_cache/`, `image_cache/`, `sandboxes/`, `state-snapshots/`, `cron/output/`, `cron/.tick.lock`, `worktrees/`, `pr-worktrees/`, `pr-review-worktrees/`, `pr-work/`, `pr-reviews/`, `pr-monitors/`, `usage/`, and skill hub/runtime metadata such as `skills/.hub/`, `skills/.curator_backups/`, `skills/.curator_state`, `skills/.usage.json`, and `skills/.usage.json.lock`.
5. If the backup checkout is also the target of active `<home>/.hermes/skills/...` symlinks, do not wipe/clean the whole checkout before copying: that breaks the source symlinks mid-backup and can delete the very skill files being copied. Use a separate staging clone, or update only safe subtrees (`scripts/`, `cron/jobs.json`, `my-open-prs/`, etc.) while skipping symlinks that resolve inside the destination.
6. Before commit, stage files and run a final tracked-file safety scan: verify no forbidden runtime paths are staged and grep/regex scan for common token/private-key patterns (`ghp_…`, `sk-…`, Slack `xox…`, `BEGIN … PRIVATE KEY`). Sanitize text files with example-like matches; exclude binary files that match secret-like patterns unless the user explicitly confirms they are safe.
6. Add a README documenting what is included, what is intentionally excluded, and restore steps: copy files back into `<home>/.hermes/` or a profile, recreate secrets via `.env` / `hermes login` / `hermes auth`, replace redacted placeholders if needed, then restart Hermes/gateway.
7. After pushing, verify with `gh repo view OWNER/REPO --json nameWithOwner,isPrivate,url,defaultBranchRef,pushedAt` and `git ls-remote origin refs/heads/main`. Report the local checkout path, latest commit, privacy status, inclusions/exclusions, and safety scan result.


| Section | Key options |
|---------|-------------|
| `model` | `default`, `provider`, `base_url`, `api_key`, `context_length` |
| `agent` | `max_turns` (90), `tool_use_enforcement` |
| `terminal` | `backend` (local/docker/ssh/modal), `cwd`, `timeout` (180) |
| `compression` | `enabled`, `threshold` (0.50), `target_ratio` (0.20) |
| `display` | `skin`, `tool_progress`, `show_reasoning`, `show_cost` |
| `stt` | `enabled`, `provider` (local/groq/openai/mistral) |
| `tts` | `provider` (edge/elevenlabs/openai/minimax/mistral/neutts) |
| `memory` | `memory_enabled`, `user_profile_enabled`, `provider` |
| `security` | `tirith_enabled`, `website_blocklist` |
| `delegation` | `model`, `provider`, `base_url`, `api_key`, `max_iterations` (50), `reasoning_effort` |
| `checkpoints` | `enabled`, `max_snapshots` (50) |

Full config reference: https://hermes-agent.nousresearch.com/docs/user-guide/configuration

### Providers

20+ providers supported. Set via `hermes model` or `hermes setup`.

| Provider | Auth | Key env var |
|----------|------|-------------|
| OpenRouter | API key | `OPENROUTER_API_KEY` |
| Anthropic | API key | `ANTHROPIC_API_KEY` |
| Nous Portal | OAuth | `hermes auth` |
| OpenAI Codex | OAuth | `hermes auth` |
| GitHub Copilot | Token | `COPILOT_GITHUB_TOKEN` |
| Google Gemini | API key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| DeepSeek | API key | `DEEPSEEK_API_KEY` |
| xAI / Grok | API key | `XAI_API_KEY` |
| Hugging Face | Token | `HF_TOKEN` |
| Z.AI / GLM | API key | `GLM_API_KEY` |
| MiniMax | API key | `MINIMAX_API_KEY` |
| MiniMax CN | API key | `MINIMAX_CN_API_KEY` |
| Kimi / Moonshot | API key | `KIMI_API_KEY` |
| Alibaba / DashScope | API key | `DASHSCOPE_API_KEY` |
| Xiaomi MiMo | API key | `XIAOMI_API_KEY` |
| Kilo Code | API key | `KILOCODE_API_KEY` |
| AI Gateway (Vercel) | API key | `AI_GATEWAY_API_KEY` |
| OpenCode Zen | API key | `OPENCODE_ZEN_API_KEY` |
| OpenCode Go | API key | `OPENCODE_GO_API_KEY` |
| Qwen OAuth | OAuth | `hermes login --provider qwen-oauth` |
| Custom endpoint | Config | `model.base_url` + `model.api_key` in config.yaml |
| GitHub Copilot ACP | External | `COPILOT_CLI_PATH` or Copilot CLI |

Full provider docs: https://hermes-agent.nousresearch.com/docs/integrations/providers

### Toolsets

Enable/disable via `hermes tools` (interactive) or `hermes tools enable/disable NAME`.

| Toolset | What it provides |
|---------|-----------------|
| `web` | Web search and content extraction |
| `browser` | Browser automation (Browserbase, Camofox, or local Chromium) |
| `terminal` | Shell commands and process management |
| `file` | File read/write/search/patch |
| `code_execution` | Sandboxed Python execution |
| `vision` | Image analysis |
| `image_gen` | AI image generation |
| `tts` | Text-to-speech |
| `skills` | Skill browsing and management |
| `memory` | Persistent cross-session memory |
| `session_search` | Search past conversations |
| `delegation` | Subagent task delegation |
| `cronjob` | Scheduled task management |
| `clarify` | Ask user clarifying questions |
| `messaging` | Cross-platform message sending |
| `search` | Web search only (subset of `web`) |
| `todo` | In-session task planning and tracking |
| `rl` | Reinforcement learning tools (off by default) |
| `moa` | Mixture of Agents (off by default) |
| `homeassistant` | Smart home control (off by default) |

Tool changes take effect on `/reset` (new session). They do NOT apply mid-conversation to preserve prompt caching.

---

## Security & Privacy Toggles

Common "why is Hermes doing X to my output / tool calls / commands?" toggles — and the exact commands to change them. Most of these need a fresh session (`/reset` in chat, or start a new `hermes` invocation) because they're read once at startup.

### Secret redaction in tool output

Secret redaction is **off by default** — tool output (terminal stdout, `read_file`, web content, subagent summaries, etc.) passes through unmodified. If the user wants Hermes to auto-mask strings that look like API keys, tokens, and secrets before they enter the conversation context and logs:

```bash
hermes config set security.redact_secrets true       # enable globally
```

**Restart required.** `security.redact_secrets` is snapshotted at import time — toggling it mid-session (e.g. via `export HERMES_REDACT_SECRETS=true` from a tool call) will NOT take effect for the running process. Tell the user to run `hermes config set security.redact_secrets true` in a terminal, then start a new session. This is deliberate — it prevents an LLM from flipping the toggle on itself mid-task.

Disable again with:
```bash
hermes config set security.redact_secrets false
```

### PII redaction in gateway messages

Separate from secret redaction. When enabled, the gateway hashes user IDs and strips phone numbers from the session context before it reaches the model:

```bash
hermes config set privacy.redact_pii true    # enable
hermes config set privacy.redact_pii false   # disable (default)
```

### Command approval prompts

By default (`approvals.mode: manual`), Hermes prompts the user before running shell commands flagged as destructive (`rm -rf`, `git reset --hard`, etc.). Approval is currently global/session/pattern based — there is no separate “trust commands from this skill only” switch. When a user asks how to auto-approve commands from skills, explain these choices clearly:

- `manual` — always prompt (default)
- `smart` — use an auxiliary LLM to auto-approve low-risk commands, prompt on high-risk; recommended for trusted skill workflows that still need a safety gate
- `off` — skip normal approval prompts globally (equivalent to YOLO; not recommended unless the user accepts the risk)

```bash
hermes config set approvals.mode smart       # recommended middle ground for skills
hermes config set approvals.mode off         # bypass normal prompts globally (not recommended)
hermes gateway restart                       # needed for gateway sessions
```

Per-session/per-invocation bypass without changing config:
- Gateway/chat session: `/yolo` toggles session-scoped YOLO; run `/yolo` again to disable
- CLI invocation: `hermes --yolo …`
- Process env: `export HERMES_YOLO_MODE=1`

Cron/scheduled skill runs are non-interactive. Dangerous commands are denied by default unless explicitly enabled:
```bash
hermes config set approvals.cron_mode approve
hermes gateway restart
```

When an approval prompt appears, “Always Approve” / `/always` persists the matched dangerous-command pattern in `command_allowlist`. Warn that this is pattern-based and applies beyond the current skill. Even with YOLO / `approvals.mode: off` / cron approve mode, Hermes still hard-blocks catastrophic commands such as root filesystem deletion, disk formatting/raw block writes, shutdown/reboot, and fork bombs.

Note: YOLO / `approvals.mode: off` does NOT turn off secret redaction. They are independent.

### Shell hooks allowlist

Some shell-hook integrations require explicit allowlisting before they fire. Managed via `<home>/.hermes/shell-hooks-allowlist.json` — prompted interactively the first time a hook wants to run.

### Disabling the web/browser/image-gen tools

To keep the model away from network or media tools entirely, open `hermes tools` and toggle per-platform. Takes effect on next session (`/reset`). See the Tools & Skills section above.

---

## Voice & Transcription

### STT (Voice → Text)

Voice messages from messaging platforms are auto-transcribed.

Provider priority (auto-detected):
1. **Local faster-whisper** — free, no API key: `pip install faster-whisper`
2. **Groq Whisper** — free tier: set `GROQ_API_KEY`
3. **OpenAI Whisper** — paid: set `VOICE_TOOLS_OPENAI_KEY`
4. **Mistral Voxtral** — set `MISTRAL_API_KEY`

Config:
```yaml
stt:
  enabled: true
  provider: local        # local, groq, openai, mistral
  local:
    model: base          # tiny, base, small, medium, large-v3
```

### TTS (Text → Voice)

| Provider | Env var | Free? |
|----------|---------|-------|
| Edge TTS | None | Yes (default) |
| ElevenLabs | `ELEVENLABS_API_KEY` | Free tier |
| OpenAI | `VOICE_TOOLS_OPENAI_KEY` | Paid |
| MiniMax | `MINIMAX_API_KEY` | Paid |
| Mistral (Voxtral) | `MISTRAL_API_KEY` | Paid |
| NeuTTS (local) | None (`pip install neutts[all]` + `espeak-ng`) | Free |

Voice commands: `/voice on` (voice-to-voice), `/voice tts` (always voice), `/voice off`.

---

## Spawning Additional Hermes Instances

Run additional Hermes processes as fully independent subprocesses — separate sessions, tools, and environments.

### When to Use This vs delegate_task

| | `delegate_task` | Spawning `hermes` process |
|-|-----------------|--------------------------|
| Isolation | Separate conversation, shared process | Fully independent process |
| Duration | Minutes (bounded by parent loop) | Hours/days |
| Tool access | Subset of parent's tools | Full tool access |
| Interactive | No | Yes (PTY mode) |
| Use case | Quick parallel subtasks | Long autonomous missions |

### One-Shot Mode

```
terminal(command="hermes chat -q 'Research GRPO papers and write summary to <home>/research/grpo.md'", timeout=300)

# Background for long tasks:
terminal(command="hermes chat -q 'Set up CI/CD for <home>/myapp'", background=true)
```

### Interactive PTY Mode (via tmux)

Hermes uses prompt_toolkit, which requires a real terminal. Use tmux for interactive spawning:

```
# Start
terminal(command="tmux new-session -d -s agent1 -x 120 -y 40 'hermes'", timeout=10)

# Wait for startup, then send a message
terminal(command="sleep 8 && tmux send-keys -t agent1 'Build a FastAPI auth service' Enter", timeout=15)

# Read output
terminal(command="sleep 20 && tmux capture-pane -t agent1 -p", timeout=5)

# Send follow-up
terminal(command="tmux send-keys -t agent1 'Add rate limiting middleware' Enter", timeout=5)

```

Continuation:

```
# Exit (2)
terminal(command="tmux send-keys -t agent1 '/exit' Enter && sleep 2 && tmux kill-session -t agent1", timeout=10)
```

### Multi-Agent Coordination

```
# Agent A: backend
terminal(command="tmux new-session -d -s backend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t backend 'Build REST API for user management' Enter", timeout=15)

# Agent B: frontend
terminal(command="tmux new-session -d -s frontend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t frontend 'Build React dashboard for user management' Enter", timeout=15)

# Check progress, relay context between them
terminal(command="tmux capture-pane -t backend -p | tail -30", timeout=5)
terminal(command="tmux send-keys -t frontend 'Here is the API schema from the backend agent: ...' Enter", timeout=5)
```

### Session Resume

```
# Resume most recent session
terminal(command="tmux new-session -d -s resumed 'hermes --continue'", timeout=10)

# Resume specific session
terminal(command="tmux new-session -d -s resumed 'hermes --resume 20260225_143052_a1b2c3'", timeout=10)
```

### Tips

- **Prefer `delegate_task` for quick subtasks** — less overhead than spawning a full process
- **Use `-w` (worktree mode)** when spawning agents that edit code — prevents git conflicts
- **Set timeouts** for one-shot mode — complex tasks can take 5-10 minutes
- **Use `hermes chat -q` for fire-and-forget** — no PTY needed
- **Use tmux for interactive sessions** — raw PTY mode has `\r` vs `\n` issues with prompt_toolkit
- **For scheduled tasks**, use the `cronjob` tool instead of spawning — handles delivery and retry

---

## Troubleshooting

### Voice not working
1. Check `stt.enabled: true` in config.yaml
2. Verify provider: `pip install faster-whisper` or set API key
3. In gateway: `/restart`. In CLI: exit and relaunch.

### Tool not available
1. `hermes tools` — check if toolset is enabled for your platform
2. Some tools need env vars (check `.env`)
3. `/reset` after enabling tools

### Model/provider issues
1. `hermes doctor` — check config and dependencies
2. `hermes login` — re-authenticate OAuth providers
3. Check `.env` has the right API key
4. **Copilot 403**: `gh auth login` tokens do NOT work for Copilot API. You must use the Copilot-specific OAuth device code flow via `hermes model` → GitHub Copilot.

### Changes not taking effect
- **Tools/skills:** `/reset` starts a new session with updated toolset
- **Config changes:** In gateway: `/restart`. In CLI: exit and relaunch.
- **Code changes:** Restart the CLI or gateway process

### Skills not showing
1. `hermes skills list` — verify installed
2. `hermes skills config` — check platform enablement
3. Load explicitly: `/skill name` or `hermes -s name`

### Gateway issues
Check logs first:
```bash
grep -i "failed to send\|error" <home>/.hermes/logs/gateway.log | tail -20
```

If Hermes tool calls fail before the command/file read runs with a missing `<home>/.hermes/message-sessions/` path, recreate the folder and retry from a neutral working directory:
```bash
mkdir -p <home>/.hermes/message-sessions
cd /tmp
```
When shell/file tools are blocked by that startup error, use an available Python/code execution tool to create the directory first (for example `os.makedirs(os.path.expanduser("<home>/.hermes/message-sessions"), exist_ok=True)`), then retry the original log/config inspection.

Common gateway problems:
- **Gateway dies on SSH logout**: Enable linger: `sudo loginctl enable-linger $USER`
- **Gateway dies on WSL2 close**: WSL2 requires `systemd=true` in `/etc/wsl.conf` for systemd services to work. Without it, gateway falls back to `nohup` (dies when session closes).
- **Gateway crash loop**: Reset the failed state: `systemctl --user reset-failed hermes-gateway`

### Platform-specific issues
- **Telegram group bot only responds to mentions/replies**: Two independent gates can block listen-all behavior. First, in **@BotFather → /mybots → Bot Settings → Group Privacy → Turn off**, then remove and re-add the bot to the group because Telegram caches privacy state per group. Second, disable Hermes' mention gate with `hermes config set telegram.require_mention false && hermes gateway restart`, or set `telegram.free_response_chats` for only selected group chat IDs. If normal group messages still do not arrive, make the bot a group admin or re-add it after the BotFather privacy change.
- **Discord bot silent**: Must enable **Message Content Intent** in Bot → Privileged Gateway Intents.
- **Slack bot only works in DMs**: Must subscribe to `message.channels` event. Without it, the bot ignores public channels.
- **Windows HTTP 400 "No models provided"**: Config file encoding issue (BOM). Ensure `config.yaml` is saved as UTF-8 without BOM.

### Auxiliary models not working
If `auxiliary` tasks (vision, compression, session_search) fail silently, the `auto` provider can't find a backend. Either set `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`, or explicitly configure each auxiliary task's provider:
```bash
hermes config set auxiliary.vision.provider <your_provider>
hermes config set auxiliary.vision.model <model_name>
```

### Context compression timeout and connection failures
If `/compress` or automatic context compression fails with `Codex auxiliary Responses stream exceeded 120.0s total timeout`, the compression auxiliary task likely timed out while generating the summary. Raise the task-specific timeout and restart the gateway/new session so the running process reads the updated config:
```bash
hermes config set auxiliary.compression.timeout 600
hermes gateway restart  # for gateway sessions
```
Verify from the source checkout with:
```bash
python - <<'PY'
from agent.auxiliary_client import _get_task_timeout
print(_get_task_timeout('compression'))
PY
```

If the user asks “what is the connection error?” or “show me the message,” do not paraphrase from memory. Quote the exact log lines from `<home>/.hermes/logs/agent.log`, `errors.log`, or `gateway.error.log`, especially the auxiliary task line and underlying exception. A compression failure can look like:
```text
Auxiliary compression: connection error on auto (Connection error.), trying fallback
Auxiliary compression: connection error on auto and no fallback available (tried: openrouter, nous, local/custom, api-key)
Failed to generate context summary: Connection error.. Further summary attempts paused for 60 seconds.
RuntimeError: Cannot send a request, as the client has been closed.
openai.APIConnectionError: Connection error.
```
This is distinct from a timeout: the Codex/OpenAI HTTP client was already closed before the auxiliary compression request could be sent. Also inspect the compressed continuation transcript under `<home>/.hermes/sessions/<new_session_id>.jsonl` to see whether fallback placeholders were written.

See `references/context-compression-timeouts.md` for the code path, focused pytest commands, adapter-forwarding smoke test, and connection-error log triage recipe.

---

## Where to Find Things

| Looking for... | Location |
|----------------|----------|
| Config options | `hermes config edit` or [Configuration docs](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) |
| Available tools | `hermes tools list` or [Tools reference](https://hermes-agent.nousresearch.com/docs/reference/tools-reference) |
| Slash commands | `/help` in session or [Slash commands reference](https://hermes-agent.nousresearch.com/docs/reference/slash-commands) |
| Skills catalog | `hermes skills browse` or [Skills catalog](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) |
| Provider setup | `hermes model` or [Providers guide](https://hermes-agent.nousresearch.com/docs/integrations/providers) |
| Platform setup | `hermes gateway setup` or [Messaging docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/) |
| MCP servers | `hermes mcp list` or [MCP guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) |
| Profiles | `hermes profile list` or [Profiles docs](https://hermes-agent.nousresearch.com/docs/user-guide/profiles) |
| Cron jobs | `hermes cron list` or [Cron docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) |
| Memory | `hermes memory status` or [Memory docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) |
| Env variables | `hermes config env-path` or [Env vars reference](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) |
| CLI commands | `hermes --help` or [CLI reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands) |
| Gateway logs | `<home>/.hermes/logs/gateway.log` |
| Session files | `<home>/.hermes/sessions/` or `hermes sessions browse` |
| Source code | `<home>/.hermes/hermes-agent/` |

---

## Contributor Quick Reference

For occasional contributors and PR authors. Full developer docs: https://hermes-agent.nousresearch.com/docs/developer-guide/

### Project Layout

```
hermes-agent/
├── run_agent.py          # AIAgent — core conversation loop
├── model_tools.py        # Tool discovery and dispatch
├── toolsets.py           # Toolset definitions
├── cli.py                # Interactive CLI (HermesCLI)
├── hermes_state.py       # SQLite session store
├── agent/                # Prompt builder, context compression, memory, model routing, credential pooling, skill dispatch
├── hermes_cli/           # CLI subcommands, config, setup, commands
│   ├── commands.py       # Slash command registry (CommandDef)
│   ├── config.py         # DEFAULT_CONFIG, env var definitions
│   └── main.py           # CLI entry point and argparse
├── tools/                # One file per tool
```

Continuation:

```
│   └── registry.py       # Central tool registry
├── gateway/              # Messaging gateway
│   └── platforms/        # Platform adapters (telegram, discord, etc.)
├── cron/                 # Job scheduler
├── tests/                # ~3000 pytest tests
└── website/              # Docusaurus docs site
```

Config: `<home>/.hermes/config.yaml` (settings), `<home>/.hermes/.env` (API keys).

### Adding a Tool (3 files)

**1. Create `tools/your_tool.py`:**
```python
import json, os
from tools.registry import registry

def check_requirements() -> bool:
    return bool(os.getenv("EXAMPLE_API_KEY"))

def example_tool(param: str, task_id: str = None) -> str:
    return json.dumps({"success": True, "data": "..."})

registry.register(
    name="example_tool",
    toolset="example",
```

Continuation:

```python
    schema={"name": "example_tool", "description": "...", "parameters": {...}},
    handler=lambda args, **kw: example_tool(
        param=args.get("param", ""), task_id=kw.get("task_id")),
    check_fn=check_requirements,
    requires_env=["EXAMPLE_API_KEY"],
)
```

**2. Add to `toolsets.py`** → `_HERMES_CORE_TOOLS` list.

Auto-discovery: any `tools/*.py` file with a top-level `registry.register()` call is imported automatically — no manual list needed.

All handlers must return JSON strings. Use `get_hermes_home()` for paths, never hardcode `<home>/.hermes`.

### Adding a Slash Command

1. Add `CommandDef` to `COMMAND_REGISTRY` in `hermes_cli/commands.py`
2. Add handler in `cli.py` → `process_command()`
3. (Optional) Add gateway handler in `gateway/run.py`

All consumers (help text, autocomplete, Telegram menu, Slack mapping) derive from the central registry automatically.

### Agent Loop (High Level)

```
run_conversation():
  1. Build system prompt
  2. Loop while iterations < max:
     a. Call LLM (OpenAI-format messages + tool schemas)
     b. If tool_calls → dispatch each via handle_function_call() → append results → continue
     c. If text response → return
  3. Context compression triggers automatically near token limit
```

### Testing

```bash
python -m pytest tests/ -o 'addopts=' -q   # Full suite
python -m pytest tests/tools/ -q            # Specific area
```

- Tests auto-redirect `HERMES_HOME` to temp dirs — never touch real `<home>/.hermes/`
- Run full suite before pushing any change
- Use `-o 'addopts='` to clear any baked-in pytest flags

### Commit Conventions

```
type: concise subject line

Optional body.
```

Types: `fix:`, `feat:`, `refactor:`, `docs:`, `chore:`

### Key Rules

- **Never break prompt caching** — don't change context, tools, or system prompt mid-conversation
- **Message role alternation** — never two assistant or two user messages in a row
- Use `get_hermes_home()` from `hermes_constants` for all paths (profile-safe)
- Config values go in `config.yaml`, secrets go in `.env`
- New tools need a `check_fn` so they only appear when requirements are met
