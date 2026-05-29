# Codex LLM Judge

## Rubric

Judge whether the assistant selects this skill only for Codex CLI delegation, Codex quota checks, Codex-backed PR review, or Hermes Codex automation. A pass requires referencing the preserved operating guide for detailed commands instead of inventing new flags.

## Golden Cases

- Prompt: "Use Codex CLI to refactor this repo in the background." Expected: trigger this skill and follow the background protocol.
- Prompt: "Check whether my ChatGPT Codex quota is stale." Expected: trigger this skill and use the quota guidance.
- Prompt: "Review this PR manually without Codex." Expected: do not trigger this skill unless Codex is requested as the reviewer.

## Expected Output

The judge returns `pass` when routing and command selection match the rubric, otherwise `fail` with the missed condition.
