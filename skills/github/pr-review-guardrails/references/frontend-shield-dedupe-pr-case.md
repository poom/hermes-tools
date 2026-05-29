# Frontend Shield SDK over-firing / per-state dedupe PR case

Use this reference when reviewing a FINN Web/App PR that reduces Shield SDK/Attributes traffic on the frontend by removing eager initialization and deduplicating polling-driven screen sends.

## Pattern that was approve-level

Concrete case: FINN-Web-App #4918 (`fix: reduce duplicate Shield SDK and attributes traffic`).

Approve-level evidence included:

- The current diff was frontend-only; older backend `shieldSessionBind` review threads were resolved/outdated and belonged to a parent/backend PR, not the current patch.
- `AppComponent` removed eager app-start `initShield()` so unrelated routes no longer initialize Shield automatically.
- `ShieldService.sendScreenAttributes(...)` still owned the GrowthBook gate, platform eligibility, storage/user fetch, sampling, SDK init, session capture, and backend bind. The PostLogin sampling check ran before `initShieldCore()`.
- Polling call sites deduped only the repeated polling state, not the entire journey:
  - `manualCheckPage` sends once.
  - `manualCheckApproved` sends once.
  - A real `manualCheckPage -> manualCheckApproved` transition still sends twice total, once per state.
- Flow-specific screen names stayed unchanged (`StatementUpload`, `FinverseLinking`, `TruIdLinking`).
- Module-scoped services reset dedupe when a new linking attempt starts. In the concrete TruID case, `shieldTrackedStates.clear()` in `startLinking()` resolved the prior concern that one app session could suppress a later attempt.
- Regression tests covered repeated same-state suppression, real state transitions, the new-attempt reset for module-scoped TruID, and PostLogin sample exclusion preventing SDK init/bind.
- GrowthBook implementation check passed with the existing Shield POC flag retained.

## Review pitfalls

- Do not keep repeating resolved/outdated backend Attributes API blockers if the current PR no longer changes backend files. Build a thread ledger and classify those findings as stale/resolved when GraphQL review-thread state confirms `isResolved`/`isOutdated`.
- Do not approve a per-state dedupe pattern blindly in singleton/module-scoped services. Verify a reset boundary for a new user journey/linking attempt, or require one.
- Component/page-scoped Sets are usually acceptable only if lifecycle creates a new instance per attempt. If that is uncertain, mention it as a non-blocking caveat or require an explicit reset depending on risk.
- Removing eager Shield init is safe only if all intended call sites still go through the guarded `sendScreenAttributes` path and sampling/feature-flag checks happen before network/SDK work.
- FE-2510-style tickets may include a runbook update in Definition of Done. If the PR explicitly leaves it post-merge, treat it as a non-blocking follow-up unless the user/product made it a merge gate.

## Verification snippets

Useful evidence commands:

```bash
# Review threads with resolved/outdated state
gh api graphql -f owner=EWA-Services -f repo=FINN-Web-App -F number="$PR" -f query='\
query($owner:String!, $repo:String!, $number:Int!) {\
  repository(owner:$owner, name:$repo) {\
    pullRequest(number:$number) {\
      reviewThreads(first:100) { nodes { isResolved isOutdated path line comments(first:10) { nodes { author { login } createdAt body path line outdated } } } }\
    }\
  }\
}'
```

Search for the key safety properties in the diff:

```bash
git diff origin/main...HEAD -- src/app/app.component.ts src/app/shared/services/shield.service.ts 'src/app/pages/**/**/*.ts'
rg 'initShield\(|sendScreenAttributes\(|shieldTrackedStates|startLinking\(' src/app
```
