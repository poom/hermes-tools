# Machine-specific cron/config restore checklist

Use when restoring Hermes cron jobs and config backups across multiple machines that may share a Discord bot history or a config repo.

## Key lesson

Do not blindly copy one machine's `cron/jobs.json` or backup script into another machine and call it restored. Cron definitions include machine-specific names, origins, delivery targets, script behavior, workdirs, and backup repo destinations.

## Checklist

1. Identify the live machine first:
   - `hostname`
   - active Hermes profile / `$HERMES_HOME`
   - intended Discord guild/server for this machine
   - intended config backup repo/checkout for this machine
2. Inspect the active job before editing:
   - `hermes cron list --all`
   - read `$HERMES_HOME/cron/jobs.json` for exact job id/name/script/deliver/workdir fields
3. Restore only matching machine cron data:
   - Prefer per-machine backup paths, e.g. `machines/<machine>/cron/jobs.json`, over one shared `cron/jobs.json`.
   - If only one shared file exists, reconcile job-by-job instead of overwriting all jobs.
4. Verify backup scripts match the machine:
   - Destination checkout (`DST` / `HERMES_CONFIG_BACKUP_DIR`)
   - Git remote (`REMOTE` / `HERMES_CONFIG_BACKUP_REMOTE`)
   - repo label in output/README
   - absence of the other machine's hostname/repo string
5. Rename/update existing cron jobs instead of creating duplicates when ids are already present.
6. Run the deterministic backup script once and verify it pushes to the intended repo.
7. Verify after changes:
   - `hermes cron list --all` shows the intended machine suffix/name
   - `hermes cron status` says gateway scheduler is running
   - active `$HERMES_HOME/cron/jobs.json` matches the intended repo copy
   - latest commit is on the intended remote

## Pitfalls

- Same Discord bot token on two machines can make commands appear to affect both; separate tokens or servers/channels reduce confusion, but cron files still need machine-specific restore logic.
- A job name like `(r7840hs)` on a Mac is a red flag that the Ubuntu cron config was copied wholesale.
- A backup script may have been copied too; check the script constants, not just the cron job name.
- If active skills are symlinked into the backup checkout, never wipe the checkout before copying. Use a staging clone or safe subtree updates and skip symlinks resolving inside the destination.
