---
name: hermes-agent-operations
description: "Operate and maintain a live Hermes Agent install: gateway runtime debugging, config/env drift triage, skill library syncing, backups, symlinks, and machine-specific cron/config restore."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hermes-agent, gateway, skills, config-backup, symlinks, cron, runtime-debugging, operations]
    related_skills: [hermes-agent, systematic-debugging, debugging-hermes-tui-commands, skillify]
---

# Hermes Agent Operations

Use this class-level skill when maintaining a live Hermes Agent installation rather than making a one-off config edit. It covers three recurring operational classes:

1. **Gateway runtime debugging** — messaging-platform sessions, long-running status messages, config/env drift, live agent budgets, delivery targets, logs, and multi-machine bot collisions.
2. **Deterministic maintenance cron jobs** — no-agent scripts for safe cleanup/monitoring tasks such as Discord PR thread/channel closers, with dry-runs, tight scoping, quiet no-op output, and cron verification.
3. **Skills/config library operations** — auditing which skills are custom versus bundled/hub-installed, safely syncing or desymlinking skills with git-backed config repos, restoring machine-specific cron/config backup state, and maintaining shared portable scripts/skills repos for multiple Hermes instances.

Always load `hermes-agent` first when the task asks about Hermes commands, configuration, gateway, tools, profiles, cron, or skills. It contains the canonical CLI reference and current command names.

## Operating principles

- Verify the live runtime path. Do not explain Hermes behavior from config alone: gateway processes are long-lived, per-turn code can refresh env/config differently, cached agents can preserve old values, and delivery targets can be rewritten.
- Treat `$HERMES_HOME/skills` as the active live skill library. Config repos are backup/source-of-truth candidates, not automatically the active source.
- Protect upstream content. Bundled Hermes skills, optional source skills, and hub-installed skills are not user-authored just because they are present locally or absent from `.bundled_manifest`.
- Keep backups outside `$HERMES_HOME/skills` so Hermes does not discover backup folders as duplicate skills.
- Never print secrets while inspecting `.env`, config backups, bot tokens, auth files, or git repos.
- Prefer updating existing cron jobs/scripts over creating duplicates when a config-backup or monitoring job already exists.

## Gateway runtime debugging

Use this subsection when Discord/Telegram/Slack gateway behavior differs from CLI behavior, config seems ignored, status text is confusing, delivery goes to the wrong place, or two machines appear to answer as the same bot.

### Fast triage checklist

1. Load `hermes-agent` for canonical paths and commands.
2. Check configured source of truth:
   - `hermes config path`
   - inspect relevant keys in `~/.hermes/config.yaml` such as `agent.max_turns`, `agent.gateway_timeout`, `agent.gateway_notify_interval`, and `delegation.max_iterations`.
3. Check env overrides and project env files:
   - `~/.hermes/.env`
   - repo-local `.env` if the gateway loads one
   - look for `HERMES_MAX_ITERATIONS`, `HERMES_AGENT_TIMEOUT`, provider/model env vars, and platform tokens without printing token values.
4. Check the live gateway process:
   - `hermes gateway status`
   - process command/env via `ps eww -p <pid>` only when needed and with secret-safe output handling.
5. Check logs:
   - `~/.hermes/logs/gateway.log`
   - `~/.hermes/logs/gateway.error.log`
   - `~/.hermes/logs/errors.log`
   - search for channel/thread IDs, session keys, `Agent budget:`, inbound messages, response-ready events, timeout warnings, and delivery warnings.
6. Read source around the relevant status/timeout path before giving exact semantics. For long-running gateway status messages, inspect `gateway/run.py` and `run_agent.py` around agent construction and `get_activity_summary()`.

### Interpreting `Still working... (N min elapsed — iteration X/Y, ...)`

The gateway periodically sends this while a turn is active. It usually comes from `gateway/run.py`'s long-running notification task.

- `N min elapsed` is wall-clock elapsed time for the active turn notification timer.
- `X` is the live agent's API-call count / loop iteration count.
- `Y` is the `AIAgent.max_iterations` value used by that specific live agent instance.
- The trailing status is the current or last activity description, such as `receiving stream response`, `running: terminal`, or `tool completed: ...`.

Do not assume `Y` equals the current `config.yaml` value. It may reflect stale env, cached agent state, or a per-turn code path that reads env before config authority is reasserted. See `references/gateway-max-iterations-env-drift.md` for a concrete trace.

### Config/env drift pattern

A common class:

- `~/.hermes/config.yaml` says `agent.max_turns: 300`.
- `~/.hermes/.env` still contains `HERMES_MAX_ITERATIONS=60`.
- Gateway startup logs may show the expected config value.
- A per-turn path can still read `os.getenv("HERMES_MAX_ITERATIONS")` before runtime config/env refresh reasserts config authority, constructing a live `AIAgent` with the stale cap.

Short-term fix: remove/update the stale env var and restart the gateway. Code fix: refresh runtime env/config before any per-turn budget read, or recompute the budget immediately after refresh and before `AIAgent(...)` construction. Add regression coverage for config authority at startup and per-turn agent creation.

### Delivery target and thread debugging

For Discord channel/thread confusion:

1. Search logs for numeric channel and thread IDs.
2. Compare inbound `chat=<id>`, source `thread_id`, cron `deliver=...`, and resolved delivery target.
3. Watch for warnings like `origin has thread_id=... but delivery target lost it`; this means a delivery target was flattened to a parent channel.
4. For cron jobs that must preserve threads, prefer explicit `discord:<channel_id>:<thread_id>` or dynamic `send_message` target construction.

## Deterministic maintenance cron jobs

Use this subsection when the user asks to add or repair scheduled operational cleanup/monitoring jobs in Hermes, especially destructive Discord/GitHub maintenance such as closing PR review threads or deleting PR review channels.

### No-agent maintenance job pattern

1. Prefer a deterministic script under `$HERMES_HOME/scripts/` plus `no_agent: true` for jobs that do not need reasoning. The script should own discovery, validation, action, and compact stdout.
2. Add `--dry-run`, `--json`, and quiet default behavior. In no-agent cron, empty stdout means silent no-op; non-empty stdout is delivered verbatim.
3. Scope destructive actions tightly in code, not only in the prompt. For Discord PR cleanup, constrain by guild, category/parent channel, channel type, and extracted GitHub PR URL before deleting/archiving.
4. Verify external state with authoritative APIs immediately before action. For GitHub PR cleanup, use `gh api repos/{owner}/{repo}/pulls/{number}` and require `state == closed` or `merged == true`.
5. Run a dry-run with full JSON and inspect counts/candidates/errors before the first destructive run.
6. Run once manually for immediate cleanup, then run a second dry-run to verify zero remaining candidates.
7. Create/update the cron job with `no_agent: true`; keep any existing complementary job unless the user explicitly asks to replace it.
8. Verify `hermes cron list` / cronjob list shows the intended `script`, `schedule`, `enabled`, `deliver`, and `no_agent` fields.

For Discord `review-prs` text-channel auto-delete specifically, see `references/discord-pr-channel-cleanup-cron.md`.

### Multi-machine bot token collisions

If two Hermes gateways on different machines use the same Discord/Telegram bot token, the platform sees them as the same bot identity. Both gateways may receive events and execute commands.

Triage/fix:

1. Check which token/app each machine's gateway process is using without printing token values.
2. Compare the intended server/guild/channel for each machine with live gateway logs and config.
3. Prefer separate bot applications/tokens per machine when both gateways should be online.
4. Restart both gateways after token changes, then send a small test command in each intended server/channel.
5. Keep machine-specific env/config out of shared git backups.

## Skills and config library operations

Use this subsection when inspecting `~/.../hermes-config/skills`, symlinking skills, backing up or restoring skills, identifying which skills are user-authored versus bundled/upstream, desymlinking active skills, or reconciling machine-specific cron/config backup repos.

### Audit workflow

1. Resolve paths first:
   - Active skills: `$HERMES_HOME/skills` (usually `~/.hermes/skills`).
   - Candidate config repo: use the path the user gave; if absent, check obvious alternatives such as `~/hermes-config`.
   - Hermes source checkout: usually `~/.hermes/hermes-agent`; compare both `skills/` and `optional-skills/`.
2. Inventory skill names by parsing every `SKILL.md` frontmatter `name`, not just folder names.
3. Identify protected/upstream skills:
   - installed bundled skills in `$HERMES_HOME/skills/.bundled_manifest`;
   - Hermes source skills under source `skills/` and `optional-skills/`;
   - hub-installed skills in `$HERMES_HOME/skills/.hub/lock.json` or audit logs.
4. Classify custom candidates:
   - strong custom/user candidates are present in the config repo but absent from Hermes source and optional skills;
   - optional upstream skills are still upstream even when absent from `.bundled_manifest`;
   - local-only custom candidates are active skills absent from both the config repo and Hermes source.
5. Detect existing symlinks with `Path.is_symlink()` and `os.readlink()`. Preserve external source-repo symlinks unless the user explicitly asks to repoint them.
6. Detect locally patched upstream skills by hashing tree contents against Hermes source and report them separately.

Use `references/custom-skill-symlink-audit.md` for the compact probe pattern and count reconciliation rules.

### Safe symlink plan shape

Report before mutating:

```text
Checked: <repo>/skills
Active skills: <HERMES_HOME>/skills

Recommended to symlink:
- <category>/<skill>

Keep existing external symlink:
- <category>/<skill> -> <target>

Maybe include, please confirm:
- <skill>: <why ambiguous>

Do not symlink by default:
- bundled/upstream patched skills: <names>

Missing from repo:
- <local-only-custom-skill>
```

Only apply after confirmation. Move old active folders to `$HERMES_HOME/skill-backups/symlink-YYYYMMDD-HHMMSS/`, not under `$HERMES_HOME/skills`. Unlink only symlinks; preserve real targets. Verify `skill_view(name)` or `hermes skills list`, symlink targets, and `SKILL.md` presence.

### Desymlink and config-backup migration

When moving Hermes config backup from an old git-backed config repo to a machine-specific repo while removing active skill symlinks:

1. Inventory only active `$HERMES_HOME/skills` symlinks whose resolved target contains `SKILL.md`.
2. Create `$HERMES_HOME/skill-backups/desymlink-YYYYMMDD-HHMMSS/` and save metadata for each symlink.
3. Unlink each active symlink only, then copy the resolved skill directory back into the same active path with cache ignores.
4. Update the deterministic backup script constants/env defaults for the new destination, remote, and repo label.
5. Run the backup script once to push, then a second time to verify quiet no-op behavior.
6. Verify active skill symlink count, backup repo symlink count, private remote, branch, clean git status, and cron job configuration.

See `references/config-backup-desymlink-migration.md` and `references/config-backup-full-cron-and-symlink-safety.md`.

### Machine-specific cron/config restore

When restoring Hermes cron jobs or config backups across multiple machines:

1. Identify the live machine first: `hostname`, active Hermes profile / `$HERMES_HOME`, intended Discord guild/server, and intended config backup repo/remote.
2. Treat `$HERMES_HOME/cron/jobs.json` as machine-specific state. Prefer per-machine backups such as `machines/<machine>/cron/jobs.json`; otherwise reconcile job-by-job.
3. For existing config-backup jobs, update existing ids/names/scripts instead of creating duplicates.
4. Check the backup script as well as the cron job name: destination checkout, remote URL, repo label, README/output text, and stale machine-specific strings.
5. Run the deterministic backup script and verify the latest commit reached the intended remote, then verify `hermes cron list --all` and `hermes cron status`.

See `references/machine-specific-cron-config-restore.md`.

### Shared portable Hermes tools repos

When creating or maintaining a shared repo for scripts/skills used by multiple Hermes instances, make portability and rebase-only sync explicit:

1. Configure the repo for rebase/autostash (`pull.rebase=true`, `rebase.autoStash=true`, and branch rebase), and always pull with `git pull --rebase --autostash` before pushing.
2. Copy active skills from `$HERMES_HOME/skills` while excluding runtime/cache/auth state; preserve support directories so skills remain complete packages.
3. Refactor scripts to use env vars/CLI flags instead of host-specific paths, profile paths, repo names, PR numbers, or user homes. Convert one-off monitors into generic scripts plus tiny compatibility wrappers.
4. Add README guidance for restore/sync on other machines and `.gitignore` coverage for Hermes runtime state, caches, logs, auth files, and secrets.
5. Before committing, run compile/AST checks, script personal-path scans, secret regex scans, script `--help` smoke tests, and `git diff --check` / `git diff --cached --check`. Normalize copied text/template whitespace rather than skipping validation.
6. Report exact validation, commit, rebase/push, and final status output.

See `references/shared-hermes-tools-repo-sync.md` for a concrete reusable checklist.

## Verification

For gateway fixes:

1. Restart gateway (`hermes gateway restart` or platform service restart).
2. Verify startup logs show the intended budget/model.
3. Trigger a small gateway turn and confirm live status or response-ready logs use the intended cap/target.
4. If source changed, run focused tests for gateway config/env bridging plus regression tests for the specific bug.

For skill/config repo operations:

1. Verify exact paths, git remotes, and symlink targets after every move or repoint.
2. Run `skill_view(name)` or `hermes skills list` for representative skills.
3. Keep backup paths and metadata in the final report.
4. For cron/config backup changes, verify cron list/status and the pushed git commit on the intended remote.

## Pitfalls

- Do not answer from config alone; live gateway turns can use cached values or stale env.
- Do not conflate top-level `agent.max_turns` with `delegation.max_iterations`.
- Do not treat startup `Agent budget:` as definitive for every later turn without checking per-turn code/logs.
- Do not symlink the entire `skills/` directory by default.
- Do not classify optional upstream skills as user-owned only because they are non-bundled.
- Do not wipe a config repo before copying into it; active skills may be symlinks into that repo.
- Do not place backups under `$HERMES_HOME/skills`.
- Do not commit or print secrets from config repos, `.env`, token files, or auth files.
