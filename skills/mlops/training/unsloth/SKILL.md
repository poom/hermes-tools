---
name: unsloth
description: Use when applying the Unsloth Skill skill workflow: Unsloth: 2-5x faster LoRA/QLoRA fine-tuning, less VRAM. Triggered by requests mentioning unsloth, Unsloth Skill, setup, operation, troubleshooting, review, or automation for this workflow.
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [Fine-Tuning, Unsloth, Fast Training, LoRA, QLoRA, Memory-Efficient, Optimization, Llama, Mistral, Gemma, Qwen]
---
# Unsloth Skill

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `unsloth`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Index](references/index.md) - preserved detailed guidance or domain-specific operations.
- [Llms Full](references/llms-full.md) - preserved detailed guidance or domain-specific operations.
- [Llms Txt](references/llms-txt.md) - preserved detailed guidance or domain-specific operations.
- [Llms](references/llms.md) - preserved detailed guidance or domain-specific operations.
- [Preserved Skill Guide](references/preserved-skill-guide.md) - preserved detailed guidance or domain-specific operations.

## Scripts

- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
