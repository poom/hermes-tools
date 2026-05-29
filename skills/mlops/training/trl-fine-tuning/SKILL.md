---
name: trl-fine-tuning
description: Use when applying the TRL - Transformer Reinforcement Learning skill workflow: TRL: SFT, DPO, PPO, GRPO, reward modeling for LLM RLHF. Triggered by requests mentioning trl-fine-tuning, TRL - Transformer Reinforcement Learning, setup, operation, troubleshooting, review, or automation for this workflow.
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [Post-Training, TRL, Reinforcement Learning, Fine-Tuning, SFT, DPO, PPO, GRPO, RLHF, Preference Alignment, HuggingFace]
---
# TRL - Transformer Reinforcement Learning

## Protocol

1. Use this skill only when the user request matches the trigger description or explicitly names `trl-fine-tuning`.
2. Read the linked references before taking action; they preserve the detailed step-by-step procedures from the previous guide.
3. Prefer deterministic scripts for repeatable validation and use the documented smoke command before live side effects.
4. If credentials, network access, or external systems are required, run the offline checks first and then ask for or verify the required access.
5. Keep new operational detail in `references/` and keep `SKILL.md` focused on routing, protocol, and failure behavior.

## References

- [Dpo Variants](references/dpo-variants.md) - preserved detailed guidance or domain-specific operations.
- [Grpo Training](references/grpo-training.md) - preserved detailed guidance or domain-specific operations.
- [Online Rl](references/online-rl.md) - preserved detailed guidance or domain-specific operations.
- [Preserved Skill Guide](references/preserved-skill-guide.md) - preserved detailed guidance or domain-specific operations.
- [Reward Modeling](references/reward-modeling.md) - preserved detailed guidance or domain-specific operations.
- [Sft Training](references/sft-training.md) - preserved detailed guidance or domain-specific operations.

## Scripts

- `scripts/skill_health.py` - deterministic support or offline coverage for this skill.
- `scripts/test_skill_health.py` - deterministic support or offline coverage for this skill.

## Failure Behavior

- If the request does not match this skill, do not force the workflow; use the more specific skill or normal repo process.
- If a referenced command cannot run because credentials or live endpoints are unavailable, report the blocked check and continue with offline evidence.
- If the preserved guide conflicts with current repository state, verify the live files first and update the relevant reference before proceeding.
