---
name: codex-daily-usage-record
description: Use when applying the Codex Daily Usage Record skill workflow: Use when asked to check ChatGPT or Codex subscription token usage, track daily Codex token usage from local session logs, create per-machine CSV/JSON usage records, schedule Hermes cron summaries, or aggregate usage across multiple machines. Triggered by requests mentioning codex-daily-usage-record, Codex Daily Usage Record, setup, operation, troubleshooting, review, or automation for this workflow.
required-skills: []
required-binaries:
  - python3
version: 1.0.0
license: MIT
---
# Codex Daily Usage Record

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `codex-daily-usage-record`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Preserved Skill Guide](references/preserved-skill-guide.md) - preserved detailed guidance or domain-specific operations.

## Scripts

- `scripts/codex_daily_usage_record.py` - deterministic support or offline coverage for this skill.
- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test_codex_daily_usage_record.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
