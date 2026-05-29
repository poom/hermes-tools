# Config backup: full cron restore and symlink-safe copying

Use this reference when a Hermes config backup repo is used to restore a machine's cron jobs, scripts, and skills.

## Lessons

- Verify the live machine before trusting restored labels: hostname, intended Discord guild/server, intended config repo checkout, remote, and backup job name.
- `$HERMES_HOME/cron/jobs.json` is machine-specific state. A Mac and an Ubuntu box can both have a job named config backup, but their delivery targets, repo labels, bot tokens, scripts, and schedules may differ.
- If the backup repo is intended as a full restore source for that machine, `cron/jobs.json` should mirror the full active cron list. A helper that writes only the backup cron job is a different bootstrap pattern and should be explicit.
- Check the active script and the repo copy: destination path, remote URL, repo label, README/output text, and any stale machine-specific strings in comments/docstrings.
- Verify by running the deterministic backup script and checking the latest commit landed in the intended remote. Then compare active and repo script checksums and count jobs in active/repo `cron/jobs.json`.

## Symlink-safe copy pattern

Config repos can be both destination and source when active skills are symlinked into the repo. A backup script that removes the whole destination before copying can break active skill symlinks mid-run.

Safer pattern:

1. Do not wipe the whole repo checkout.
2. Clean only generated subtrees that are safe to recopy (`scripts/`, `hooks/`, `bin/`, generated reports, etc.).
3. Do not blindly clean `skills/` if any active `$HERMES_HOME/skills/...` symlink resolves into the destination repo.
4. For symlinked skills:
   - if the symlink is broken, report/skip it instead of crashing late;
   - if it resolves inside the destination repo, skip copying it onto itself;
   - otherwise copy from the resolved real source if the user wants that skill backed up.
5. Run a compile/syntax check for the backup script before scheduling it.
6. Run a secrets scan over tracked files before commit/push and sanitize examples rather than preserving token-like strings.

## Verification checklist

- `hostname` matches the machine label in the cron job and README/output text.
- Active backup script contains no stale old-machine repo names.
- Active script and repo script match after backup.
- Repo remote and latest commit are the intended repo.
- Active and repo `cron/jobs.json` contain the expected number of jobs and the expected backup job name.
- `hermes cron status` reports the gateway running and expected active job count.
