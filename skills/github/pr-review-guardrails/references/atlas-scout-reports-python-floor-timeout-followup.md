# Atlas Scout Reports Python floor + runner timeout follow-up

Use this reference for small follow-up PRs in `EWA-Services/Tools` / `atlas-scout-reports` that lower the supported Python floor and/or adjust shared external-command runner timeouts.

## Approve-level pattern

A PR that lowers `atlas-scout-reports` from Python 3.11 to 3.10 and raises the default shared runner timeout can be approve-level when all of the following hold:

- The package metadata explicitly declares the new floor, e.g. `requires-python = ">=3.10"`.
- CI exercises the declared minimum runtime, not only the newer runtime. For GitHub Actions this can be a matrix including both `3.10` and `3.11` with current-head green jobs.
- Local or CI validation proves the package imports/runs under the minimum runtime:
  - changed runner tests pass;
  - full package tests pass or the relevant current-head remote suite is green;
  - `compileall` passes under the minimum runtime;
  - the CLI entrypoint imports/runs at least a version/help command.
- The changed Python surface does not use obvious newer-only syntax/APIs beyond the declared floor.
- The timeout remains finite/bounded. A larger default such as `300.0` seconds is acceptable when it matches the production wrapper/runtime budget and is justified by live external CLI fan-out behavior.
- Existing sensitive-argument redaction and error handling are not weakened.

## Prior blocker classification

If an old inline blocker said “CI only tests Python 3.11 after lowering the package floor,” classify that thread as stale/resolved when the current diff adds Python 3.10 CI coverage and the current-head 3.10 job is green, even if the old thread remains unresolved in GitHub UI.

Do not duplicate a new inline comment for the same issue. Mention in the formal review body that the old thread is stale/resolved by the current matrix coverage.

## Process gates

Treat `policy-bot: main`, missing extra team approval, metadata refresh rows, and similar repo policy states as merge/process readiness unless they expose a current code/test failure. Do not convert them into code blockers for this follow-up pattern.

## Reviewer-lane pitfall

In scheduled rmux runs, direct Claude interactive transport can still get stuck at a tool-permission prompt (for example MCP/Notion/Drive) even when the prompt asks for no tools. If the lane idles at a permission prompt or only echoes the prompt without a substantive verdict, kill the rmux session, record Reviewer B as unavailable/transport-stalled, and synthesize from refreshed GitHub evidence plus the completed Codex/parent review. Do not wait indefinitely or treat the pasted prompt as reviewer output.
