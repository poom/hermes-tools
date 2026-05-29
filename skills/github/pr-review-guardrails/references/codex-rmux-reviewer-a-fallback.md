# Codex CLI / rmux fallback for Reviewer A

Use this when the normal Hermes/ChatGPT Reviewer A lane (`delegate_task` or provider-backed subagent) errors, interrupts, or produces no usable structured result during a PR review.

## When to use

- Reviewer A fails with model/provider errors, transport interruption, or no substantive output.
- The PR still needs an OpenAI/Codex-style independent lane before parent synthesis.
- Direct repo inspection and Reviewer B can continue, but an additional Reviewer A pass would materially improve confidence.

Do **not** spend unlimited time here. If Codex CLI has auth/quota/model failures after a quick probe, mark Reviewer A unavailable and continue with direct inspection + Reviewer B rather than blocking the review.

## Pattern

1. Keep Codex report-only:
   - no GitHub posting
   - no Discord/Telegram/platform messages
   - no file edits
   - return verdict/findings only for parent synthesis
2. Run inside the already-checked-out PR repo.
3. Prefer explicit model `gpt-5.5`.
4. Use PTY/rmux for interactive robustness; capture output to a durable file.
5. Smoke-test first when auth/model state is uncertain:

```bash
cd "$REPO"
codex exec --model gpt-5.5 --sandbox read-only "Say OK and do not edit files"
```

If the smoke test works, run the review prompt. If it fails with auth/quota/model errors, record `Reviewer A: unavailable (Codex CLI fallback failed: <short reason>)`.

## Minimal review prompt requirements

Include:

- PR URL, repo, base, current head SHA.
- Local checkout path.
- The task-specific risk profile (for example Firebase Functions app-factory extraction risks).
- Explicit report-only instruction.
- Required output shape: verdict, blockers, high-priority non-blockers, tests/checks considered, confidence/uncertainty.

## Synthesis rule

Treat Codex CLI fallback output as an independent Reviewer A result only after the parent verifies it is substantive and current-head scoped. If the output is partial, stale, or mostly prompt echo, ignore it and say Reviewer A was unavailable.
