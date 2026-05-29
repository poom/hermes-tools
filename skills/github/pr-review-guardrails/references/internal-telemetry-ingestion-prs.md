# Internal telemetry ingestion PR reviews

Use this reference when a PR adds or changes internal developer/tool telemetry, usage dashboards, Edge Functions, Supabase/Postgres storage, Grafana dashboards, or local hooks that collect agent/CLI activity.

## Review focus

1. **PII and payload minimization**
   - Verify the client does not transmit prompt text, command text, file contents, secrets, raw hostnames, raw remote URLs with query strings, or arbitrary tool input/output.
   - Prefer bounded metadata/counters: event type, timestamp, model/source, repo slug, command first word, prompt/command character counts.
   - If emails or identity fields are stored, require explicit documentation and access controls; hashed identifiers alone are not anonymization when email is also retained.
   - Remote repo normalization should only expose trusted-host `owner/repo`; otherwise hash the full remote rather than storing it.

2. **Token and subprocess hygiene**
   - Ingest tokens should be read from env/identity stores and removed from child-process environments before invoking `git`, CLI version probes, package managers, or installer subprocesses.
   - Installation/bootstrap scripts should not leak tokens through argv, generated hook files, shell traces, world-readable config files, or piped stdin prompts.
   - Hook failure should not break the developer workflow; fail closed/no-op for missing endpoint/token and return success for non-critical telemetry errors unless debug mode is explicitly enabled.

3. **Server-side validation and auth**
   - Require bearer/token authentication with constant-time comparison or equivalent.
   - Enforce body-size caps, JSON parsing errors, timestamp freshness bounds, allowed event names, field length limits, integer bounds, and a safe shape for command metadata (for example first word only via a conservative regex).
   - Ensure raw/untrusted payload storage is disabled or intentionally empty unless there is a documented retention/access-control reason.

4. **Database/RLS/read-access safety**
   - Check RLS is enabled for raw and identity tables, default anon/authenticated reads are denied, and dashboard/BI access uses a dedicated least-privilege read-only role.
   - Security-definer triggers/functions should pin `search_path` and avoid granting write paths through dashboard roles.
   - Views used for dashboards should not accidentally broaden access to raw PII beyond the intended reader role.

5. **Grafana/Postgres SQL safety**
   - Dashboard variables supplied through URLs are untrusted. PostgreSQL data-source queries should use Grafana formatting such as `${var:sqlstring}` instead of raw `'$var'` string interpolation.
   - Time-range panels should query the source event table with `$__timeFilter(...)` unless the view is explicitly designed for the selected range. A fixed recent-activity view can silently undercount long dashboard ranges.
   - Add regression tests that parse dashboard JSON and assert safe variable formatting plus correct source tables/time filters for high-level metrics.

6. **Workflow/deployment gates**
   - Provisioning workflows that use Grafana/Postgres secrets should be manual or environment-gated, use least repository permissions (`contents: read` when possible), and avoid checking out/running PR-controlled code with broad credentials unless justified.
   - Documentation should say which data is collected/stored, which secrets are required, and that secret values must not be committed.

## Approve-level evidence

- Current-head tests pass for hook payload construction, installer/token permissions, server validation, migration SQL, dashboard JSON/SQL, and provisioning script behavior.
- Prior unresolved threads about dashboard SQL/time windows are either resolved or confirmed outdated with current code/test evidence.
- Formal review body distinguishes code approval from process/UI noise such as outdated unresolved threads or policy-bot merge gates.

## Common blocker patterns

- Raw prompt text, command text, arbitrary tool input/output, hostnames, or untrusted remote URLs are stored without a documented product/security requirement.
- Token remains available to subprocesses or is embedded into installed hook scripts/config files with weak permissions.
- Dashboard SQL interpolates URL-controllable variables directly into string literals.
- RLS is absent or a public/authenticated role can read identity/raw telemetry tables.
- A panel uses a fixed 30-day view for a user-selectable 90-day/longer dashboard range without clear labeling.
