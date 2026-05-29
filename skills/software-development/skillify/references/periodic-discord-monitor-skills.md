# Periodic Discord Monitor Skills

Use this reference when turning a one-off reporting script into a durable scheduled skill that posts to Discord only when state changes.

## Pattern

1. Keep the detector deterministic: a script should emit machine-readable actions such as `create_channel`, `post_update`, `ping_stale`, and `post_closed` via `--actions-json`.
2. Keep side effects outside detection: Discord sends, channel creation/deletion, and mark-posted mutations should happen only after the corresponding API call succeeds.
3. Persist human-readable state as Markdown with a machine-readable metadata comment. Include IDs needed for idempotence, e.g. `channel_id`, `message_id`, `last_posted_signature`, `current_signature`, and timestamps.
4. Use one durable status directory named after the skill, e.g. `<hermes-home>/<skill-name>/`, and include it in config backup if the status must survive sessions/machines.
5. Bundle deterministic API helpers under the skill's `scripts/` directory, not as `/tmp` or external runtime scripts. Add offline tests for each helper.
6. For Discord PR/status monitors, prefer normal per-item channels under the configured parent/category when threads would make the parent channel messy. Delete the per-item channel only after a close/merge notice is successfully posted to the parent.
7. Scheduled jobs should be quiet: `deliver: local`; return `[SILENT]` when there are no actions or all posts succeeded.

## Rename/migration checklist

When renaming a promoted monitor skill, update all live and backup artifacts in one pass:

- skill folder, `SKILL.md` frontmatter, docs, script names, test names, integration/eval/smoke references
- status directory and metadata comment prefix inside every status file
- environment variable prefixes used by scripts
- cron job name, workdir, attached skill name, prompt, and any origin metadata if it will be backed up
- Discord parent channel name and managed child-channel topics, if user asked to rename Discord surface area
- backup sync allowlist/reporting/docs and backup copy
- persistent memory entries that name the old convention

Pause the cron job before path/status migration and resume only after tests, smoke, skill gate, and backup sync pass.

## Verification set

- Unit tests from the directory expected by imports.
- Smoke test with fixture JSON and a temporary status dir.
- Skillify gate for the renamed/promoted skill.
- Live `--actions-json` sanity check: pending actions should target existing channels/status IDs, not recreate migrated resources.
- Search live skill/status/cron/backup for old names. Historical logs/cache may keep old names; do not rewrite them unless they affect runtime or backup cleanliness.
- Backup repo clean and pushed after final sync.
