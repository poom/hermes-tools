# Codex rmux report-only PR reviews

Use this pattern when Codex is needed as an independent reviewer lane and the parent agent must synthesize/post the result.

## When to use

- Hermes/delegate-based GPT reviewer lane fails or is interrupted.
- User explicitly asks to test/use Codex CLI as a fallback reviewer.
- You need an output file that survives context interruption and can be read by the parent agent before any GitHub/Discord action.

## Pattern

Run inside the checked-out PR repo. Use read-only sandbox and make the prompt explicitly report-only.

```bash
cat > /tmp/run_codex_pr_review.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
REPO="/path/to/pr-checkout"
PROMPT="/tmp/pr-reviewer-prompt.md"
OUT="/tmp/pr-codex-rmux-review.out"
STATUS="/tmp/pr-codex-rmux-review.status"
rm -f "$OUT" "$STATUS"
cd "$REPO"
{
  echo "codex_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  codex exec --model gpt-5.5 --sandbox read-only --skip-git-repo-check "$(cat "$PROMPT")"
```

Continuation:

```bash
  code=$?
  echo "codex_exit $code $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "$code" > "$STATUS"
  exit "$code"
} > "$OUT" 2>&1
SH
chmod +x /tmp/run_codex_pr_review.sh
rmux kill-session -t codex-pr-review 2>/dev/null || true
rmux new-session -d -s codex-pr-review /tmp/run_codex_pr_review.sh
```

Poll/read:

```bash
if rmux has-session -t codex-pr-review 2>/dev/null; then
  rmux capture-pane -t codex-pr-review -p | tail -120
else
  cat /tmp/pr-codex-rmux-review.status
  tail -220 /tmp/pr-codex-rmux-review.out
fi
```

## Prompt requirements

Include:

- `report-only`
- no GitHub posting, no platform messages, no file edits
- exact repo path, PR URL, base/head SHA
- prior comments/blockers and local validation already performed
- required output fields: verdict, blockers with file/line evidence, notes, validation performed

## Synthesis rule

Codex output is an advisory lane. Before posting anything:

1. Parent agent reads the output/status file.
2. Parent verifies plausible findings directly in the checkout.
3. Parent re-checks live PR head before any GitHub review.
4. Parent may disagree with Codex when live PR state adds merge/process blockers (for example current-main conflicts) that the code-review lane did not classify as implementation blockers.

## Notes

- A smoke check can be `codex exec --model gpt-5.5 --sandbox read-only --skip-git-repo-check 'print CODEX_SMOKE_OK only'`.
- `codex login status` can be less useful than a tiny live `codex exec` probe.
- rmux detached sessions are useful because the result persists even if the parent turn is interrupted.
