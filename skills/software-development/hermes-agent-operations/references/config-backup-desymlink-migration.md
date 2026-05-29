# Config backup desymlink migration

Use this when moving Hermes config backup from an old git-backed config repo to a machine-specific repo while removing active skill symlinks.

## Preconditions

- Active skills root is `$HERMES_HOME/skills`.
- Old config repo may be a source for active skill symlinks.
- New backup repo is private and machine-specific.
- Secrets and runtime state must not be committed.

## Checklist

1. Inspect current backup script and cron job.
   - Identify existing `hermes_config_backup_sync.py` or equivalent deterministic no-agent script.
   - Prefer updating the existing daily cron job instead of creating a second backup job.
2. Inventory symlinks.
   - Count symlinks under `$HERMES_HOME/skills` only; avoid broad scans under all of `$HERMES_HOME` because worktrees and node_modules can produce huge noisy output.
   - For each symlink, resolve the target and require a `SKILL.md` under it before treating it as a skill.
3. Convert active symlinked skills to physical copies.
   - Create `$HERMES_HOME/skill-backups/desymlink-YYYYMMDD-HHMMSS/`.
   - Save one metadata file per symlink with active path, symlink target, and resolved path.
   - Unlink the symlink only.
   - Copy the resolved skill directory back to the same active path with cache ignores (`__pycache__`, `.DS_Store`, pytest/mypy/ruff caches, `*.pyc`).
   - Do not delete or mutate the old repo target.
4. Patch backup script constants.
   - Destination: new checkout path, e.g. `$HOME/Projects/hermes-config-r7840hs`.
   - Remote: new private repo, e.g. `git@github.com:poom/hermes-config-r7840hs.git`.
   - Repo label used in output should match the new repo.
   - Keep `.env`, auth files, state DBs, sessions, logs, caches, worktrees, cron output, skill hub/cache metadata ignored.
5. Run backup script.
   - First run should clone/init, copy safe inputs, redact literal API keys, sanitize secret-like text examples, commit, and push.
   - Second run should return exit 0 with no changes/output if no-agent quiet-on-noop is working.
6. Verify.
   - `gh repo view owner/repo --json nameWithOwner,isPrivate,url,defaultBranchRef,pushedAt` confirms private/default branch.
   - `git status --short --branch` is clean and tracking origin.
   - `git ls-remote origin refs/heads/main` matches the latest local commit.
   - Active skill symlink count is 0.
   - Backup repo symlink count is 0.
   - Backup repo contains the expected `SKILL.md` count.
7. Cron.
   - Update the existing job name to include the machine label.
   - Keep schedule (for example `0 3 * * *`) unless the user asks otherwise.
   - Keep `script: hermes_config_backup_sync.py` and `no_agent: true`.

## Reporting shape

Use the user's compact backup style:

```text
Backup success

Files/folders:
- Local repo: <path>
- Remote: <owner/repo>
- Private: yes
- Branch: main
- Commit: <short-sha>
- Included: ...

Symlinks:
- Converted <n> active skill symlinks into real copied skill folders.
- Active skill symlinks now: 0
- Backup repo symlinks now: 0
- Symlink metadata backup: <path>

Daily backup:
- Job: <id>
- Schedule: <cron>
- Mode: no-agent script

Safety:
- Secrets scan: passed
- Redacted/sanitized: ...
- Removed: ...
```
