# Country-scoped SMS / OTP copy PR reviews

Use this reference when a PR changes SMS, OTP, notification, or transactional-message copy for a specific country/route while leaving shared translation helpers in place.

## Core risk

A country-scoped copy requirement can be undermined when the message builder still chooses text by mutable `user.language` instead of by the country/route that owns the requirement.

Concrete failure pattern:

- Ticket says PH OTP messages sent through a specific SenderID must remove brand text and send only the OTP value.
- PR updates the PH/English translation to `""` or an unbranded string.
- The runtime path still calls a shared helper such as `getTranslation("WITHDRAW_OTP", user.language)` for PH users.
- Other language translations (`th`, `id-id`, etc.) still contain the brand, and user language can be changed independently from user country.
- Result: PH users with non-PH/non-English stored language still receive branded copy on the country-scoped route.

## Review checklist

1. Identify the runtime key used to choose the message body:
   - `country`, route/template type, SenderID, or provider template ID is usually safer for country-scoped requirements.
   - `user.language` alone is risky when the requirement is country/provider-specific.
2. Check whether `language` and `country` can diverge:
   - User update schema / profile endpoints.
   - Existing user data migration history.
   - Defaults inferred from IP country vs stored profile language.
3. Search all translations for the changed key, not just the locale touched by the PR:
   - Brand strings (`FINN`, legal names, sender names).
   - Provider-specific banned copy.
   - Empty-string translations that become load-bearing behavior.
4. Verify all affected flow/template aliases:
   - Registration OTP.
   - Login OTP.
   - Withdrawal confirmation OTP.
   - Reset PIN or other explicitly excluded templates remain unchanged.
5. Require regression tests for cross-product combinations, not only the happy locale:
   - Country = target country, language = default language.
   - Country = target country, language = at least one non-target language that still has the old translation.
   - Assert exact body when the ticket requires exact copy; otherwise assert forbidden brand/provider text is absent.

## Blocker wording pattern

`<country>` users can still receive the old/branded copy when their stored language is `<language>` because `<message builder>` resolves `<translation key>` using `user.language` while the requirement is scoped to `<country/provider/template>`. Since `<schema/path>` allows language to differ from country and the `<language>` translation still contains `<forbidden text>`, this remains a reachable production path. Key the message by country/template or return the approved country-scoped body before consulting language translations, and add regression coverage for `<country> + <language>`.

## Approve-level signals

- The country/provider-specific branch returns the approved copy independently of mutable language when the ticket requires one body for all users in that country/route.
- Tests cover language/country divergence for the changed paths.
- Explicitly excluded paths (for example Reset PIN) are covered or inspected and unchanged.
- Remote CI for the relevant functions/services passes; process/bot review failures are separated from the copy correctness decision.
- If a rebase/force-push changes the head during a scheduled review but the live `base...HEAD` PR-owned diff is byte-for-byte identical to the already-reviewed diff, reviewer conclusions may be carried forward after a fresh current-head/duplicate-review check. Update the review body to quote the new head and never report `approved` unless the pulls reviews API verifies a current-head formal approval.

## Case studies

- `references/finn-web-app-5025-country-otp-copy-case.md` — PH OTP copy removal, mutable `user.language` blocker, approval-level country-first fix, and force-push/base-refresh cutoff handling.
