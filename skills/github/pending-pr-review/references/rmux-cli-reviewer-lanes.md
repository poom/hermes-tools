# rmux CLI reviewer lanes for pending PR review

Use this when scheduled pending-PR review runs are failing because long in-process model/delegation calls stall or hit cron idle timeout. The pattern keeps Hermes as the orchestrator, but moves the expensive PR-review reasoning into external Codex/Claude CLI processes launched under `rmux`/`tmux` with explicit shell/Python timeouts and redirected output files.

## When to use

- Pending-review cron jobs hit `idle for 601s` or similar while reviewer/subagent/model calls are running.
- A whole batch loses progress when one reviewer/provider stalls.
- The user asks for one-PR-at-a-time processing and one-by-one Discord results.
- You need durable reviewer artifacts that survive tmux/rmux panes exiting.

## Core pattern

1. Discover the queue with the pending-review list script and choose exactly one PR.
2. Re-fetch live PR metadata, checks, comments, reviews, review threads, and current head SHA before review.
3. **Run the duplicate-current-head decision gate before launching any rmux reviewer lanes.** If Poom already has a formal `APPROVED` or `CHANGES_REQUESTED` review whose `commit_id` equals the current `headRefOid`, skip Codex/Claude entirely, report the PR as already reviewed on the current head, and classify why it is still listed (policy/process/merge blocked). This saves the cron budget and avoids duplicate reviews for raw-pending-but-already-decided PRs.
4. Build a single reviewer prompt file containing the PR context and explicit instruction: do not post to GitHub, do not modify files, return structured findings only.
4. Launch independent reviewer lanes through `rmux` (or `tmux`) that run local CLI tools:
   - Codex CLI, read-only sandbox, no approval prompts.
   - Claude Code CLI **interactive mode without `-p`** for subscription-plan compatibility. Prefer the helper script `scripts/rmux_claude_interactive_reviewer.py`, which starts `claude --tools ''` in rmux/tmux, pastes the prompt via a mux buffer, captures the pane to a file, waits for a completion sentinel or idle prompt, and kills the session.
5. Redirect durable output to files under a per-PR temp directory. Do not rely only on pane scrollback; finished rmux sessions can disappear and lose scrollback.
6. Wrap each lane in a hard timeout. If one lane times out, record that lane as timed out and continue synthesizing from available evidence.
7. Poll sessions/output files periodically so the Hermes cron job remains active and partial output is visible.
8. Synthesize reviewer outputs, then re-fetch current head and current-head reviews immediately before any GitHub action.
10. If the same actor already has a formal review on the current head with the same decision, do not post a duplicate review; report/record that the current-head decision already stands.
11. Send the per-PR result immediately via `send_message` when running under scheduled cron; do not wait for the whole queue.

## Minimal launcher shape

```bash
ROOT=/tmp/pending-pr-review-rmux/<repo>-<pr>
REPO="$ROOT/repo"
PROMPT="$ROOT/reviewer_prompt.md"
mkdir -p "$ROOT/rmux"

rmux kill-session -t pr-review-codex 2>/dev/null || true
rmux kill-session -t pr-review-claude 2>/dev/null || true

rmux new-session -d -s pr-review-codex \
  "cd '$REPO' && python3 '$ROOT/codex_reviewer.py'"

# Claude Reviewer B: no `-p`; drive interactive Claude Code inside rmux/tmux.
python "${HERMES_HOME:-$HOME/.hermes}/skills/github/pending-pr-review/scripts/rmux_claude_interactive_reviewer.py" \
  --session pr-review-claude \
  --workdir "$REPO" \
  --prompt-file "$PROMPT" \
  --output-file "$ROOT/rmux/claude.out" \
  --timeout-seconds 1800
```

Use small Python wrappers when prompts are large; passing a full PR prompt through shell quoting is fragile. For Codex, each wrapper should read `reviewer_prompt.md`, run the CLI with `timeout=...`, write combined stdout/stderr to `rmux/<lane>.out`, and append a sentinel like `__CODEX_EXIT:0__` or `__CODEX_EXIT:124__`. Prefer the observed-compatible Codex shape `codex exec --model gpt-5.5 --sandbox read-only --cd "$REPO" "$PROMPT_TEXT"`; avoid adding unsupported approval flags unless `codex exec --help` on the live host confirms them. For Claude, prefer `rmux_claude_interactive_reviewer.py`; it appends `__CLAUDE_EXIT:0__`, `__CLAUDE_TIMEOUT__`/`__CLAUDE_EXIT:124__`, or an orchestration error sentinel.

## Verification checklist

- Both reviewer output files exist or a timeout sentinel explains the missing lane.
- Output files include final exit sentinels (`__CODEX_EXIT:*__`, `__CLAUDE_EXIT:*__`).
- Claude lane used interactive Claude Code without `-p` when subscription-plan compatibility is required; output came from `rmux_claude_interactive_reviewer.py` or an equivalent mux-driven wrapper.
- Local cheap checks have run when possible (`git diff --check`, JSON validation such as `jq empty`, format checks if toolchain exists).
- Live PR head SHA after synthesis matches the head SHA reviewed, or the run aborts/restarts on the new head.
- Current-head formal reviews are inspected before posting to avoid duplicates.
- The user-facing result distinguishes transport result (rmux worked/timed out) from PR verdict (approve/request changes/comment/no duplicate post).

## Pitfalls

- Do not rely on `rmux capture-pane` for completed short-lived sessions; redirect/copy output to files from the start. For interactive Claude, continuously write captured pane text to the output file and use a no-markdown sentinel such as `HERMESCLAUDEREVIEWDONE7F3C2A`; leading/trailing underscores can be rendered away by the TUI.
- Do not put `-p` in the Claude scheduled Reviewer B path if the subscription plan may disallow print mode. Use `claude --tools ''` inside rmux/tmux and paste the prompt after startup/trust handling.
- Do not let a failed/slow reviewer lane block the entire queue. Treat it as lane-level failure and continue with available evidence if enough remains for a safe verdict.
- Do not post a duplicate GitHub review when the same actor already has a current-head formal decision and the verdict is unchanged.
- Do not mark an explanation of Terraform state drift as resolving an apply-safety blocker unless the current Digger/plan no longer applies the unrelated changes or owner sign-off explicitly accepts them.
- If a tool-call ceiling or runtime cutoff hits after one or more PRs were posted but before the final re-list, the final/local log must not imply queue completion. Include the last live queue snapshot, every verified GitHub review id/state/commit, which Discord targets already received messages, and the exact caveat `final live queue clearance was not re-verified`.
