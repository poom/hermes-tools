# Sequential rmux Claude startup-idle variants

In scheduled pending-review drains, the interactive Claude wrapper can fail before the prompt is actually submitted. The captured pane may show only the Claude Code startup screen, a sample prompt such as `Try "how do I log an error?"`, and `gh auth login · ← for agents`, with no `⏺` assistant output, no verdict, and no completion sentinel.

Treat this as a Reviewer B transport stall, not a substantive review and not a reason to wait until the full 1800s timeout:

1. Poll/capture `rmux/claude.out` and, if needed, `rmux capture-pane -t <session> -p`.
2. If the pane contains only the startup prompt/TUI footer (sample prompt text may vary) plus `gh auth login` and no assistant response/verdict, kill the rmux session.
3. Append/record a clear transport note such as `interactive Claude rmux stalled at startup prompt; no substantive review`.
4. Mark Reviewer B as unavailable/transport-stalled and continue parent synthesis from refreshed GitHub/local evidence plus any other usable lane.
5. Do not treat pasted prompt text or the startup screen itself as Reviewer B output.

This is a durable transport pattern, not a code-review finding. It should be reported in the per-PR user-facing result when it affected the run.
