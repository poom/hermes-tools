# Claude interactive reviewer sentinel prompt-echo pitfall

Session-derived note for `scripts/rmux_claude_interactive_reviewer.py` and similar rmux/tmux Reviewer B lanes.

## Pitfall

If the completion sentinel string appears verbatim inside the prompt body, the interactive Claude pane can echo the prompt and the wrapper may detect the sentinel before Claude produces a substantive review. The process may exit successfully with markers such as sentinel found / `__CLAUDE_EXIT:0__`, but the captured output contains only prompt echo, status text, or idle noise.

This is a transport false-positive, not a Reviewer B verdict.

## Prevention

- Do not include the exact sentinel token in the visible prompt text unless the wrapper distinguishes prompt echo from assistant output.
- Phrase the instruction indirectly when possible, or have the wrapper append the sentinel requirement out-of-band.
- Keep a short second-pass prompt ready when the first capture is prompt echo only.

## Validation

After each interactive Claude lane, inspect the captured output before using it:

1. Confirm it contains a substantive verdict/reasoning section, not just the pasted prompt.
2. Treat `__CLAUDE_EXIT:0__` plus sentinel as necessary but not sufficient.
3. If only prompt echo/idle noise is present, rerun with a shorter prompt and no literal sentinel echo; mark the first lane as a transport false-positive.
4. Do not post or synthesize a GitHub review from the echoed prompt.

## Compact recovery wording

```text
Reviewer B first run was ignored as a sentinel prompt-echo false-positive; reran with a shorter prompt and used only the substantive second output.
```
