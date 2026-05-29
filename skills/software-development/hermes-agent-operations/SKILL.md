---
name: hermes-agent-operations
description: Use when applying the Hermes Agent Operations skill workflow: Operate and maintain a live Hermes Agent install: gateway runtime debugging, config/env drift triage, skill library syncing, backups, symlinks, and machine-specific cron/config restore. Triggered by requests mentioning hermes-agent-operations, Hermes Agent Operations, setup, operation, troubleshooting, review, or automation for this workflow.
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [hermes-agent, gateway, skills, config-backup, symlinks, cron, runtime-debugging, operations]
    related_skills: [hermes-agent, systematic-debugging, debugging-hermes-tui-commands, skillify]
---
# Hermes Agent Operations

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `hermes-agent-operations`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Config Backup Desymlink Migration](references/config-backup-desymlink-migration.md) - preserved detailed guidance or domain-specific operations.
- [Config Backup Full Cron And Symlink Safety](references/config-backup-full-cron-and-symlink-safety.md) - preserved detailed guidance or domain-specific operations.
- [Config Repo Relocation And External Symlinks](references/config-repo-relocation-and-external-symlinks.md) - preserved detailed guidance or domain-specific operations.
- [Custom Skill Symlink Audit](references/custom-skill-symlink-audit.md) - preserved detailed guidance or domain-specific operations.
- [Discord Pr Channel Cleanup Cron](references/discord-pr-channel-cleanup-cron.md) - preserved detailed guidance or domain-specific operations.
- [Gateway Max Iterations Env Drift](references/gateway-max-iterations-env-drift.md) - preserved detailed guidance or domain-specific operations.
- [Machine Specific Cron Config Restore](references/machine-specific-cron-config-restore.md) - preserved detailed guidance or domain-specific operations.
- [Preserved Skill Guide](references/preserved-skill-guide.md) - preserved detailed guidance or domain-specific operations.
- [Shared Hermes Tools Repo Sync](references/shared-hermes-tools-repo-sync.md) - preserved detailed guidance or domain-specific operations.

## Scripts

- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
