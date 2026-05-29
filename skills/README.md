# Skills

This directory is a shared Hermes **skill overlay**, not a full copy of Hermes Agent skills.

Keep only:

- custom skills that do not exist in the Hermes Agent built-in skill tree
- locally modified skills that intentionally override or extend a built-in skill

Do not keep:

- unmodified Hermes built-in/default skills
- archive/runtime/cache metadata such as `.archive`, `.hub`, `.usage.json`, `.curator_*`, `__pycache__`, `.DS_Store`
- secrets, auth files, tokens, `.env`, or machine-specific state

## Current inventory

This snapshot contains 26 shared skills:

- `autonomous-ai-agents/codex` - local modification of a Hermes built-in skill
- `autonomous-ai-agents/codex-daily-usage-record` - custom/local skill
- `autonomous-ai-agents/hermes-agent` - local modification of a Hermes built-in skill
- `engineering-tools/environment-harness` - custom/local skill
- `github/github-code-review` - local modification of a Hermes built-in skill
- `github/github-pr-workflow` - local modification of a Hermes built-in skill
- `github/my-open-prs` - custom/local skill
- `github/pending-pr-review` - custom/local skill
- `github/pending-pr-review-github-issues-queue` - custom/local skill
- `github/pr-review-guardrails` - custom/local skill
- `gog` - custom/local skill
- `mlops/inference/outlines` - custom/local skill
- `mlops/training/axolotl` - custom/local skill
- `mlops/training/trl-fine-tuning` - custom/local skill
- `mlops/training/unsloth` - custom/local skill
- `productivity/google-workspace` - local modification of a Hermes built-in skill
- `productivity/greenhouse-recruiting` - custom/local skill
- `productivity/linear` - local modification of a Hermes built-in skill
- `productivity/notion` - local modification of a Hermes built-in skill
- `productivity/recruiter-cli` - custom/local skill
- `software-development/hermes-agent-operations` - custom/local skill
- `software-development/hermes-agent-skill-authoring` - local modification of a Hermes built-in skill
- `software-development/pickup-linear-ticket` - custom/local skill
- `software-development/requesting-code-review` - local modification of a Hermes built-in skill
- `software-development/skillify` - custom/local skill
- `software-development/systematic-debugging` - local modification of a Hermes built-in skill

## Restore to a Hermes instance

Use overlay copy, not delete-sync:

```bash
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
mkdir -p "$HERMES_HOME/skills"
rsync -a skills/ "$HERMES_HOME/skills/"
```

Do not use `rsync --delete` for skills unless you intentionally want this repo to become the entire active skill tree on that machine. Normal target machines should keep their built-in/default Hermes skills from their Hermes install.

Start a new Hermes session after syncing skills.
