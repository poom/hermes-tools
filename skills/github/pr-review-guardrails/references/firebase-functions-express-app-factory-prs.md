# Firebase Functions Express app-factory PR reviews

Use this reference when a PR extracts an Express app construction path from a Firebase Functions `index.ts`/handler file into a reusable `createApp()` or similar factory for integration testing.

## Key review risks

- **Runtime parity:** Verify middleware order stayed equivalent after extraction: cookie/CORS/proxy gates, auth/anonymous-ID middleware, raw body handling, JSON/urlencoded parsers, upload/file parsing, security headers, route prefix rewrites, logging, request/response sanitization, and router mounting.
- **Cloud Function wiring:** Keep production function export/`onRequest` registration in the Firebase entrypoint. The app factory should not import `firebase-functions/v1` or register scheduled/trigger functions as a side effect.
- **Environment-gated routes:** Debug/docs routes must remain non-production only and preserve auth/basic-auth behavior where applicable.
- **Raw-body/webhook semantics:** If raw body is needed only for selected webhook routes, check route-prefix matching carefully so broad parser changes do not break signatures or apply raw-body capture too widely.
- **Proxy/IP gates:** Re-check `trust proxy`, `req.ip`/`req.ips`, CDN/Cloudflare allowlists, localhost/test bypasses, legacy-domain bypasses, and fail-closed behavior on cache/API errors.
- **Compliance/logging:** Confirm request/response logging and sanitization still run in the same order and no PII/secrets are newly logged.
- **Preview/deploy workflows:** If an API prefix or function name moved to the new app file, update any preview-deploy sed/rename logic to target the new file. Check private-package vendoring and temporary credential cleanup in workflows.

## Approve-level evidence

- Unit or integration tests exercise the old behavior through the new factory: prefix rewrite, raw-body route scoping, CDN/IP gate exemptions/denials, debug route gating, response logging/sanitization, and proxy behavior.
- A test or mock guard proves `createApp()` can be imported without importing Firebase Functions/triggers.
- Current remote functions tests and relevant lint/Sonar/security checks pass when local dependency installation requires private credentials.
- Live review threads/comments were checked and unresolved current comments are classified as nits/suggestions or resolved/stale rather than silently ignored.

## Non-blocking patterns

- Local Jest may be skipped when `node_modules` is absent and installing would require private package credentials; record this and rely on current-head CI rather than triggering credential-dependent installs from the review host.
- Failed AI-review/metadata checks can be process noise when logs show only a wrapper/codex-job failure and current code/security CI plus human review evidence are approve-level. Inspect the failed logs before downgrading.
