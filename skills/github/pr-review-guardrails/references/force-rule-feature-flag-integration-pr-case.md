# Force-rule feature-flag integration PR case

Use this as a concrete approve-level pattern for PRs that remove a GrowthBook/feature-flag wrapper after a force-rule / 100% rollout decision.

## Case: Account-Creation-Flow #645 (BE-2995) — stacked Python feature-flag cleanup

Context:
- Linear cleanup ticket required promoting `ROHIT-za-limit-setting-refactor-BE-2539` in Account-Creation-Preparation: remove the temporary flag declaration/evaluation, always use the refactored ZA limit configuration resolver, delete the legacy-main-branch flag-off lambda path, preserve the resolver's local-formula fallback for users without a `za_limit_setting` strategy, update tests, and avoid unrelated TH/PH/ID behavior changes.
- The PR was stacked on a non-main base (`rohits/be-2994-cleanup-rohit-underwriting-context-builder-refactor-flag`), so the review diff had to use the live PR `baseRefName`, not `main`.

Approve-level evidence:
- `feature_flags.py` removed only the refactor flag constant; repository search found no remaining tracked references to `za_limit_setting_refactor`, `BE-2539`, `legacy_main_branch`, or `za_limit_refactor_enabled`.
- `lambda_function.py`'s ZA branch unconditionally called `resolve_za_limit_configuration(...)` and unpacked the same outputs as the former flag-ON path.
- `libs/countries/za_limits.py` still handled no-strategy users with the local formula fallback and still evaluated the separate `ROHIT-za-legacy-credit-limit-to-35-BE-2822` flag, preserving 0.035 vs 0.05 default-withdrawal behavior.
- Touched tests/stubs removed the deleted refactor-flag plumbing while retaining ZA LSS success/fallback/error coverage; TH/PH/ID branches were not changed in the PR-owned diff.
- Local verification used a host fallback because `poetry` was unavailable and host pytest lacked the repo's `pytest-testdox` plugin: `PYTHONPATH=Account-Creation-Preparation python3 -m pytest -o addopts='' ...` passed targeted tests; canonical remote CI remained the primary signal.

Process/check nuance:
- A duplicate matrix scenario (`za-local-formula-fallback-preserved` matching `za-control-limit-rounding-preserved`) was a valid non-blocking cleanup nit, not a request-changes-level code blocker. If an AI-review/process check escalates this kind of redundant-test nit to MUST-FIX while direct review and CI are approve-level, report it as a process/check gate separately from the code verdict.
- Existing inline notes for the duplicate scenario should not be duplicated; mention the follow-up in the summary/body only.

## Case: FINN-Web-App #4994 (FE-2304 / FE-2020) — TH paid-surveys GrowthBook force-rule cleanup

Context:
- Linear force-rule ticket FE-2304 required integrating `FAIQ-FE-2020-Paid-Surveys-V1-TH`: remove the TH GrowthBook condition/wrapper, keep the feature as if the flag is always ON, remove unused imports/dependencies, test integrated behavior, and keep the separate PH paid-surveys flag intact.
- Original FE-2020 paid-surveys context noted product/monetary sensitivity and that the feature should not go live before Mixpanel instrumentation and production testing with the Thai team; for the cleanup review, treat FE-2304's later Rollout/force-rule result as the direct experiment-outcome evidence.

Approve-level evidence:
- `PaidSurveysV1TH.service.ts` deleted, `FAIQ-FE-2020-Paid-Surveys-V1-TH` removed from `experiment-keys.index.ts`, and repo search found no remaining references to the TH key/helper (`PaidSurveysV1TH`, `paidSurveysV1TH`, `paidSurveysExperimentKeyServiceTh`).
- The three former TH gates followed the enabled path directly: main tab visibility no longer depends on the TH flag, `DashboardExtendedService.resolveRewardedSurveyBanner` returns true for TH, and `AppBannersComponent` shows rewarded survey for TH by country check.
- The PH rollout stayed independent: `PaidSurveysV1PHExperimentKeyService` remained imported/injected and `paidSurveysV1PH.isOn() && country === ph` behavior was preserved.
- Specs were updated for TH-on-by-default and PH-gated behavior. A duplicate `dashboard-extended.service.spec.ts` assertion thread was non-blocking cleanup, not a blocker.
- Local dependency installation/tests may be blocked by private Credolab registry credentials on this host. In that case, use remote CI logs as ground truth: for #4994, Test Coverage run `26240339076` passed on the reviewed head with frontend `5378/5378 SUCCESS`, functions tests passed, and SonarCloud frontend/functions passed. Still run lightweight local checks such as `git diff --check` and reference searches.
- `gh pr checks` can show stale failed metadata-gate rows after an earlier failing AI-review refresh; inspect later `gh run list` / run details before treating them as current blockers. For #4994, a later metadata-gate run passed on the same head while `policy-bot: main` remained a process gate.

## Case: FINN-Web-App #4993 (FE-2471 / FE-2020) — PH paid-surveys GrowthBook force-rule cleanup

Context:
- Linear force-rule ticket FE-2471 required integrating `FAIQ-FE-2020-Paid-Surveys-V1-PH`: remove the PH GrowthBook condition/wrapper, keep the feature as if the flag is always ON, remove unused imports/dependencies, test integrated behavior, and keep the separate TH paid-surveys flag intact.
- Original FE-2020 paid-surveys context includes monetary/product sensitivity. For cleanup review, the later force-rule result is direct outcome evidence, but still verify that the cleanup does not expand beyond the intended country/flag boundary.

Approve-level evidence:
- `PaidSurveysV1PH.service.ts` deleted, `FAIQ-FE-2020-Paid-Surveys-V1-PH` removed from `experiment-keys.index.ts`, and repo search found no remaining references to the PH key/helper (`PaidSurveysV1PH`, `paidSurveysV1PH`, `paidSurveysExperimentKeyServicePh`).
- The former PH gates followed the enabled path directly: `DashboardExtendedService.resolveRewardedSurveyBanner` returns true for PH and `AppBannersComponent` shows rewarded survey for PH by country check.
- The TH rollout stayed independent: `PaidSurveysV1THExperimentKeyService` remained imported/injected and `paidSurveysV1TH.isOn() && country === th` behavior was preserved.
- Specs were updated for PH-on-by-default, continued TH gating, unsupported/missing-country cases, repeated initialization, and TH service error propagation.
- No live inline review threads or prior human `CHANGES_REQUESTED` reviews existed.
- Local dependency installation/tests may be blocked by private Credolab registry credentials on this host. Use remote CI logs as ground truth when green: for #4993, frontend tests passed `5379/5379 SUCCESS`, functions tests passed, and SonarCloud frontend/functions passed. Still run lightweight local checks such as `git diff --check` and reference searches.

Process/check nuance:
- The title check can fail if the PR title lacks a Conventional Commit prefix (`FE-2471: ...`); treat as a process/Release Please gate, not a code blocker.
- `finn-ai-coder / review` may fail from tool/Codex infrastructure even when workflow env records `CODEX_VERDICT=APPROVE` and no code findings. Treat this as a process/metadata gate unless live AI-review output contains a concrete blocker.
- `policy-bot: main` pending remains a merge/process gate after approve-level code review.

## Case: FINN-Web-App #4947 (FE-2505 / FE-2429)

Context:
- Linear force-rule ticket said to integrate `YABETSE-Fix_Mixpanel_Anonymous_Authenticated_Merge-FE-2429` permanently: remove the feature-flag condition/wrapper, keep the enabled behavior, remove unused imports/dependencies, and test the integrated functionality.
- Original feature DoD required Mixpanel Simplified ID Merge: client forwards SDK `$device_id`; backend SIGN_UP/SIGN_IN events include `$device_id` and `$user_id`; no legacy `mixpanel.alias()` path; frontend calls `identify()` after JWT sign-in; questionnaire-passed event moves to frontend after identify.

Approve-level evidence:
- Code search found no remaining TypeScript references to the retired GrowthBook flag key, backend flag constant, frontend experiment service, `mixpanel-id-merge`, `associateAnonymousId`, `mixpanelClient.alias`, or executable `.alias(` usage.
- The prior blocker was resolved by removing the backend alias wrapper and its obsolete test.
- Signup/login always attempted to forward the Mixpanel SDK `$device_id`, while explicitly ignoring fallback IDs used only for local bucketing.
- Backend auth tracking always emitted `$user_id` and optional `$device_id`; absence of `$device_id` still tracked the authenticated event without legacy alias fallback.
- Backend questionnaire finalize no longer emitted onboarding tracking; frontend emitted questionnaire-passed after custom-token sign-in and Mixpanel `identify()`.
- Regression tests covered backend event properties, no-device fallback, frontend device-ID forwarding, fallback-ID exclusion, fail-open lookup errors, and questionnaire event movement.

Process/check nuance:
- Older `CHANGES_REQUESTED` reviews can keep `reviewDecision` stale until a current-head approval is posted.
- `gh pr checks` may show a failed `finn-ai-coder / review` refresh for the current head even when a later metadata-gate run passes and human/manual dual review is approve-level. Treat this as a process/merge gate unless the user explicitly asks to enforce it as a code-review blocker.
- Posting a human approval may trigger a new queued metadata-gate row. Briefly poll if useful, but do not silently monitor for long; report it as a still-settling process gate when finalizing.

Review checklist for similar force-rule cleanup PRs:
1. Read the force-rule ticket and original feature/experiment DoD; distinguish rollout decision from A/B outcome.
2. Search for both flag identifiers and behavior-specific legacy APIs, not just the flag constant.
3. Verify the kept path is active without a remote flag dependency and failure behavior is still safe.
4. Verify the removed path cannot be re-entered through helper wrappers, stale services, tests, comments-as-code examples, or generated configs.
5. Require tests around both the new always-on behavior and important fail-open/no-data cases.
6. Separate process/metadata gates from code blockers in the final verdict.
