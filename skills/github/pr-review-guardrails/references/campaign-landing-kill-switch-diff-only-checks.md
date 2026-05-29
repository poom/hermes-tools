# Campaign landing kill-switch PRs and diff-only GrowthBook check false positives

Use this when a PR adds campaign-landing registry entries/components that are gated by an existing, unchanged campaign landing guard/service, and an automated GrowthBook implementation check fails because it only sees the PR diff.

## Pattern

A PR may add new campaign pages like `/landing/<country>/<slug>` by adding:

- `campaign-landing.registry.ts` entries
- campaign component templates/SCSS/specs
- module declarations
- route-specific copy/SEO metadata

while the actual feature-flag enforcement remains in unchanged shared code such as:

- `landing-routing.module.ts` with a guarded `:country/:campaign` route
- `CampaignLandingGuard`
- `CampaignLandingExperimentKeyService`

A diff-only GrowthBook audit can incorrectly fail with notes like “the diff does not show GrowthBook-gated invocation” or “new routes are registered unconditionally.” Treat that as a finding to verify, not automatically as a blocker.

## Review steps

1. Verify there is no direct route to the new component that bypasses the campaign guard.
2. Confirm `:country/:campaign` routes use `CampaignLandingGuard` (or equivalent) and that the guard checks the feature flag before registry lookup/render.
3. Confirm missing/malformed/false flag values fail closed to the normal landing fallback, not to the new campaign component.
4. Compare key construction with PR/ticket/flag JSON entries, including lowercasing/canonical slug handling.
5. Inspect registry entries for exact country/slug/canonical path/component consistency and `indexable: false` when pages are paid/experiment landing pages.
6. Check CTA links use shared/dynamic signup hrefs rather than design-source hard-coded links, and that specs cover href binding and regression against removed hard-coded links.
7. Read unresolved review threads and latest author replies before carrying forward older blockers.
8. If the code path is safe but the automated GrowthBook check failed because it was diff-only, report it as a process-gate false positive/override candidate, not a code blocker.

## Evidence that supports approval

- Existing guard/service are unchanged but live in the active route path.
- Guard performs flag check before render/registry resolution.
- `isEnabled` or equivalent returns true only for explicit boolean true and defaults to false.
- PR body/ticket documents the exact flag key/map entries to enable before production traffic.
- Remote tests/pre-commit pass, and local diff checks pass.
- Review threads covering earlier bypass/style/link issues are resolved or stale on the current head.

## CSS-only follow-up fixes after campaign landing rollout

A later PR may only fix shell/layout regressions introduced by the campaign landing rollout, while still mentioning the original GrowthBook flag/ticket in the PR body. Treat this as a CSS/layout follow-up rather than a new experiment implementation when the live diff does not add routes, registry entries, flags, or campaign components.

Concrete Ionic/Angular pattern to verify:

- The global desktop shell clamp may target `.ion-page ion-content`, `.ion-page ion-header`, or `.ion-page ion-footer` with `max-width: 350px !important`.
- Ionic can apply `.ion-page` to both the root `<ion-app>` shell and the routed page host (`<app-landing>` / `<app-campaign-landing>`), so fixing only the inner routed host can still leave the outer `ion-content` clamped.
- A safe outer-shell release can scope to the active routed page host with selectors like `ion-app.ion-page:has(app-landing:not(.ion-page-hidden)) > ion-content` and the campaign-landing equivalent. The `:not(.ion-page-hidden)` qualifier is important because `IonicRouteStrategy` may keep prior pages mounted but hidden after navigation; unqualified `body:has(app-landing)` or `ion-app:has(app-landing)` can leak full-width layout to login/onboarding/main after the first landing visit.
- Check browser support against the repo target, but for desktop-only `@media (min-width: 420px) and (pointer: fine)` rules the failure mode may be the pre-fix clamped layout rather than a new safety regression. Mention this as non-blocking when appropriate.

When the GrowthBook implementation check fails on such a CSS-only follow-up, classify it as a process/diff-only false positive if:

- The route guard/service still enforces the existing kill-switch path.
- The PR has an explicit no-experiment/override comment or equivalent product/process approval.
- The current substantive tests/checks pass and no live review threads identify a real flag-off behavior regression.

## Non-blocking caveats to mention

- Operational flag entries still need to be added/enabled before traffic promotion.
- A Sonar duplication gate may fail for intentionally self-contained variant pages; accept only when the ticket/PR explicitly chooses independent variant iteration/revertability and process owners can override or accept the gate.
- If components expose `sectionView` outputs but never emit them, note that internal section-view analytics will be absent unless external CAC/conversion measurement is the accepted experiment design.
