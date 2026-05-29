# FINN-Web-App #5025 — PH OTP copy with mutable language

Session case study for country-scoped SMS/OTP copy reviews.

## PR shape

- Repo/PR: `EWA-Services/FINN-Web-App#5025`
- Ticket: BE-3016, remove FINN branding from Philippines webapp OTP templates when the backup route uses the `Take-off` SenderID.
- Intended scope:
  - PH registration OTP: OTP value only.
  - PH login OTP and withdrawal confirmation OTP: OTP value only.
  - Reset PIN SMS body intentionally unchanged.

## Original blocker pattern

The first implementation updated PH/English copy but still built PH login/withdrawal OTPs through a shared translation helper keyed by `user.language`:

```ts
getTranslation("WITHDRAW_OTP", user.language)
```

That left a reachable branded path for PH users whose stored language was `th` or `id-id`, because those translations still contained `FINN` and profile language can diverge from country.

## Approve-level fix pattern

The approved shape was a country-first runtime branch before translation lookup:

```ts
if (user.country === CountryCodeEnum.ph) {
  return `${otp}`;
}
```

Registration used the same country-scoped idea in the OTP service: PH registration sends exactly `${otp}` while non-PH behavior remains unchanged.

Regression coverage that made the fix reviewable:

- helper-level tests for PH users with default, Thai, and Indonesian language values returning OTP-only;
- login OTP test for PH + `language: th` asserting digit-only and no `FINN`;
- withdrawal OTP test for PH + Indonesian language asserting exact OTP-only body;
- registration OTP service test asserting exact OTP-only body;
- explicit inspection that Reset PIN copy stayed unchanged.

## Process/check handling

Passing remote functions/frontend tests and SonarCloud were enough to rely on the focused coverage. A failing `finn-ai-coder / review` / metadata refresh row that only refreshed a previous workflow failure (`failure (none)`) was process noise, not a new code blocker, once the live diff and review evidence showed the blocker resolved.

## Force-push/base-refresh pitfall

During the scheduled review run, the head changed while posting was about to happen. The correct recovery was:

1. Abort the stale approval immediately.
2. Fetch the new head and actual base branch.
3. Recompute the live `base...HEAD` PR-owned diff.
4. Compare it to the reviewed diff. In this case it was byte-for-byte identical even though the commit SHA changed due to a base refresh/force-push.
5. Update the review body to quote the new current head and re-run the duplicate-current-head review check before posting.

If tool budget cuts off after offline approval/revalidation but before GitHub review submission, report the PR as **reviewed offline / no GitHub review posted / no final per-PR result sent**. Do not call it approved unless the pulls reviews API verifies a current-head formal approval.
