# hermes-tools

Shared Hermes overlay for multiple Hermes instances (Mac, Ubuntu, or profiles).

This repository is **not** a mirror of Hermes Agent itself. It keeps only the pieces that should move between Poom's Hermes machines:

- reusable scripts
- custom skills
- locally modified skills that intentionally override a Hermes built-in skill

Hermes built-in/default skills should come from each machine's Hermes installation, not from this repo.

## Layout

- `scripts/` - reusable cron/helper scripts. Scripts must resolve host-specific values from environment variables or command-line arguments, not hardcoded machine paths.
- `skills/` - shared skill overlay only: custom skills plus local modifications to built-in skills. It intentionally excludes unmodified Hermes built-in/default skills.

## Rebase-only git workflow

This repository is shared by multiple Hermes machines. Do not merge-forward local histories.

Recommended once per checkout:

```bash
git config pull.rebase true
git config rebase.autoStash true
git config branch.main.rebase true
```

Before editing:

```bash
git pull --rebase --autostash origin main
```

After editing:

```bash
git status --short
git add scripts skills README.md .gitignore
git commit -m "chore: update shared Hermes tools"
git pull --rebase --autostash origin main
git push origin main
```

If a rebase conflicts, resolve the files, run `git rebase --continue`, then push. Do not run `git merge origin/main`.

## Install or update a Hermes instance

Set `HERMES_HOME` if you are using a profile; otherwise it defaults to `~/.hermes`.

```bash
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

# Scripts: safe to sync as a shared toolbox.
mkdir -p "$HERMES_HOME/scripts"
rsync -a --delete scripts/ "$HERMES_HOME/scripts/"
chmod +x "$HERMES_HOME/scripts"/*.py

# Skills: overlay only. Do NOT --delete the whole active skill tree.
# This preserves built-in/default Hermes skills installed on the target machine.
mkdir -p "$HERMES_HOME/skills"
rsync -a skills/ "$HERMES_HOME/skills/"
```

After updating skills, start a new Hermes session (`/reset` in gateway/chat or restart the CLI/gateway) so the skill loader sees the changes.

## Updating `skills/` from a machine

Only copy shared skills into this repo:

1. Keep skills that do **not** exist in the Hermes Agent built-in skill tree.
2. Keep skills that exist in Hermes Agent but are intentionally modified locally.
3. Exclude unmodified Hermes built-in/default skills.
4. Exclude archive/runtime/cache metadata: `.archive`, `.hub`, `.usage.json`, `.curator_*`, `__pycache__`, `.DS_Store`.

Useful comparison sources on a normal install:

```bash
USER_SKILLS="${HERMES_HOME:-$HOME/.hermes}/skills"
BUILTIN_SKILLS="${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}/skills"
```

## Portable script configuration

Common env vars used by scripts:

- `HERMES_HOME` - active Hermes home/profile directory; default `~/.hermes`.
- `HERMES_SCRIPTS_DIR` - where helper scripts live; default `$HERMES_HOME/scripts`.
- `HERMES_ENV_FILE` - dotenv file to load; default `$HERMES_HOME/.env`.
- `HERMES_EXTRA_PATHS` - extra binary directories, separated by `:` on macOS/Linux.
- `HERMES_TOOLS_TIMEZONE` - timezone for reminder/triage scripts; default `Asia/Bangkok`.

Secrets stay outside git in each machine's environment or `$HERMES_HOME/.env`.

## Safety policy

Do not commit:

- `$HERMES_HOME/.env`, `auth.json`, OAuth tokens, credential pools.
- Session logs, state DBs, cache, generated media, cron output, worktrees.
- Skill hub/curator runtime metadata (`skills/.hub`, `.usage.json`, `.curator_*`, `.archive`).
- Unmodified Hermes built-in/default skills.

Run validation and a secret scan before pushing when changing copied files.
