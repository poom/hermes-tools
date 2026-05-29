# Vendor Attributes API rollout safety

Use this reference when reviewing PRs that move client-side identity/attribute attachment into a backend vendor Attributes API (fraud, risk, analytics, attribution, device-intelligence, etc.).

## Review checks

1. **Preserve non-identity client SDK signals**
   - Moving `user_id` or other sensitive identity fields server-side does not automatically mean all client SDK calls should be removed.
   - Re-check whether native/web SDK calls also carry checkpoint, screen, lifecycle, device, or event context that vendor rules/analytics depend on.
   - If prior review or vendor guidance says only identity moves backend, treat removal of non-PII SDK checkpoint calls as a blocker unless author provides vendor-confirmed equivalence.

2. **Avoid partial-success bind semantics**
   - Watch for endpoints that persist local bind/backfill state and then call an external vendor API inside the same request.
   - If the vendor call fails after local state commits and the handler returns `500`, clients see failure while local state is already written. This can create ambiguous retries and leave vendor identity attachment missing.
   - Require one of:
     - durable attributes status (`pending`/`sent`/`failed`) plus retry/outbox,
     - idempotent vendor send tracking such as `attributesSentAt` and retry-on-unsent,
     - or explicit non-fatal behavior with telemetry and a documented reconciliation path.

3. **Per-session vs per-checkpoint idempotency**
   - Do not let a single session-level `attributesSentAt` / `already_sent` flag suppress later checkpoint or screen attributes unless the vendor/product contract explicitly says only one checkpoint per session should be sent.
   - If the old client SDK emitted attributes on every `sendScreenAttributes(screen)` call, moving identity to a backend Attributes API must either preserve the non-identity client SDK signal or make the backend send idempotent per `(sessionId, screen)` / checkpoint.
   - A common unsafe shape: frontend removes Android `sendAttributes(...)` and web `getDeviceIntelligence({userAttrData})`; backend forwards the first `screen` to the vendor and records later screens only in local Firestore/timeline after `attributesSentAt` exists. Treat this as a blocker because Shield/vendor dashboards and rules only see the first screen, not later product checkpoints.
   - Ask for a regression test that calls bind/send for two different screens on the same session and proves both checkpoint labels reach the vendor or the explicitly approved replacement path.

4. **Feature-flag/safe rollout**
   - Verify flag OFF preserves old behavior.
   - For flag ON, verify both identity attachment and existing non-identity signals still flow.
   - If the ticket requires dashboard confirmation, keep that as a rollout note; do not require it before code approval unless it is the stated merge gate.

5. **Deduplicate comments**
   - If an existing inline thread already covers a missing SDK checkpoint/signal, do not post a duplicate inline comment. Reference that the existing thread remains blocking in the formal review body.
   - Post new inline comments only for newly discovered blockers, e.g. backend partial-success/idempotency gaps.

## Example blocker language

> The PR removes the client-side per-screen attribute call and replaces it with a backend Attributes send guarded by a single session-level `attributesSentAt`. Because `sendScreenAttributes(...)` is invoked from multiple checkpoints, Shield will only receive whichever `screen` wins the first send; later screens are only recorded locally and never forwarded to the vendor. Keep `user_id` server-side, but preserve non-identity checkpoint telemetry either by retaining a client SDK screen call without identity or by making backend Attributes idempotent per `(sessionId, screen)` with tests.

> This endpoint commits the local bind/backfill before the vendor Attributes API call, then returns 500 if the vendor call throws. That leaves the client seeing a failed bind even though local state was already written, and there is no durable sent/retry/outbox state to guarantee the identity attachment eventually succeeds or to prevent ambiguous repeated vendor calls on retries. For safe rollout, make this side effect explicitly idempotent/durable instead of coupling the API response to a post-commit external call.
