---
name: google-workspace
description: Use when applying the Google Workspace skill workflow: Gmail, Calendar, Drive, Docs, Sheets via gws CLI or Python. Triggered by requests mentioning google-workspace, Google Workspace, setup, operation, troubleshooting, review, or automation for this workflow.
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [Google, Gmail, Calendar, Drive, Sheets, Docs, Contacts, Email, OAuth]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [himalaya]
---
# Google Workspace

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `google-workspace`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Gmail Search Syntax](references/gmail-search-syntax.md) - preserved detailed guidance or domain-specific operations.
- [Preserved Skill Guide](references/preserved-skill-guide.md) - preserved detailed guidance or domain-specific operations.
- [Sheets Scenario Models](references/sheets-scenario-models.md) - preserved detailed guidance or domain-specific operations.

## Scripts

- `scripts/_hermes_home.py` - deterministic support or offline coverage for this skill.
- `scripts/google_api.py` - deterministic support or offline coverage for this skill.
- `scripts/gws_bridge.py` - deterministic support or offline coverage for this skill.
- `scripts/setup.py` - deterministic support or offline coverage for this skill.
- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test__hermes_home.py` - deterministic support or offline coverage for this skill.
- `scripts/test_google_api.py` - deterministic support or offline coverage for this skill.
- `scripts/test_gws_bridge.py` - deterministic support or offline coverage for this skill.
- `scripts/test_setup.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
