# Dependabot PolicyBot bypass safety

Session pattern: EWA-Services/EWA-Actions #454 (BE-2980) attempted to let `dependabot[bot]` bypass human approvals after required checks pass. The risky shape was a new `approval_rules` branch with `requires.count: 0` and only `has_valid_signatures: true` in some shared templates, while another template included explicit `has_status` checks.

## Review checklist

When a PR adds or changes a PolicyBot/required-review bypass for Dependabot or another automation actor:

1. Confirm the bypass is limited to the automation identity:
   - `has_author_in` or equivalent matches the exact bot login.
   - `only_has_contributors_in` or equivalent prevents human follow-up commits from inheriting the bypass.
   - `allow_author: false` remains in place unless there is a documented reason.
2. Confirm the bypass still gates on required safety checks, not just signatures:
   - Look for `has_status` (or the repo/org equivalent) covering CI, security, static analysis, and any required dependency-update checks.
   - If the template omits local `has_status` because checks are centralized elsewhere, require explicit proof/mapping for each affected template/repo class. A comment in AGENTS.md saying checks are centralized is not enough by itself.
   - Compare all sibling templates. Inconsistent safety gates across backend/serverless/trunk-based templates are a blocker unless clearly intentional and proven safe.
3. Treat shared-template blast radius as part of merge safety:
   - Identify the sync manifest/downstream repo classes affected.
   - Ask for a staged rollout/canary or rollback path when the bypass changes many repos at once.
4. Separate process checks from code/config blockers:
   - Stale `metadata-gate / Refresh finn-ai-coder review check`, AI-label, or PolicyBot rows can be process readiness notes if current replacement checks pass.
   - Missing status gates in the bypass rule itself is a code/config blocker because it changes the enforcement contract.
5. Recommended fix directions:
   - Add the appropriate `has_status` block to every automation bypass rule, or
   - provide explicit centralized-policy evidence proving the missing checks are enforced for every affected template class.

## Wording for a blocker

> The new Dependabot zero-review bypass in `<policy template>` requires `count: 0` and only `has_valid_signatures`, with no `has_status` CI/security gate. The ticket/PR says Dependabot should bypass human metadata/review friction only after required checks pass. Because this template syncs downstream, please add the required status checks or provide explicit centralized-policy coverage per affected repo class.
