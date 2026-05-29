# Terraform alert webhook fallback reviews

Use this reference for Terraform/Grafana/alerting PRs that add a new contact point, webhook URL variable, or notification route while reusing an existing alert-channel configuration.

## Session pattern

In `EWA-Services/monitoring-infrastructure #320`, a new Finn Runners Grafana contact point initially introduced a parallel webhook URL fallback. Existing Checkly alert routing supported both:

1. a flat `checkly_alert_webhook_url`, and
2. a nested object path `checkly_alert_webhook.url`.

The new contact point only considered the flat URL, so Terraform plans could fail or alert routing could regress for environments using the supported nested object path. A later fix made the new contact point fall back to the existing normalized local (`local.checkly_alert_webhook_url`), which preserved both paths.

## Review checklist

- Search for existing webhook/contact-point locals before approving a new URL fallback chain.
- Verify new contact points reuse the same normalized local/fallback semantics as existing channels instead of duplicating partial logic.
- Check both variable shapes when the repo supports a migration/compatibility path: flat variables and nested object attributes.
- Treat a dropped supported fallback as request-changes-level when it can break Terraform plan/apply or silently route alerts to the wrong/missing destination.
- On re-review, classify the old blocker as resolved only after checking current code and live review threads/author replies; an outdated unresolved-looking inline comment may be resolved in GraphQL after a later reply.
- Prefer current Digger/Terraform plan evidence for infra safety; if local `terraform`/`tofu` is unavailable, state the local limitation and rely on current successful remote plans plus focused code inspection.

## Approve-level evidence

- The new contact point uses the existing normalized local or exactly preserves its fallback order.
- Remote Digger/Terraform plans pass for affected environments and show expected create/update counts with no unexplained destroys/replacements.
- Prior fallback-regression review threads are resolved or clearly stale/outdated after an author reply and current-code verification.
