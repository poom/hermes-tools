# Google Sheets scenario-model tabs

Use this when the user asks to build a new Sheets tab for budget/scenario analysis, especially when `gog sheets update` is too limited for formulas, formatting, adding tabs, or batch updates.

## Workflow

1. Read current workbook shape and source data first:
   ```bash
   gog sheets metadata SPREADSHEET_ID --account work --json --results-only
   gog sheets get SPREADSHEET_ID "'Source tab'!A1:Z100" --account work --json --results-only
   ```
2. If formulas/formatting/new tabs are needed, use Google Sheets API directly. `gog sheets` can read/write values, but direct API is more reliable for `addSheet`, `batchUpdate`, value formulas with `USER_ENTERED`, formatting, and verification.
3. For existing `gog` auth, export the refresh token temporarily and refresh an access token locally. `gog auth tokens export` refuses to overwrite an existing output file, so remove any stale temp token first:
   ```bash
   mkdir -p /tmp/sheets_work
   rm -f /tmp/sheets_work/work_token.json
   gog auth tokens export phathaisarn.c@example.com --client work --output /tmp/sheets_work/work_token.json --json >/dev/null
   ```
   Load OAuth client credentials from:
   `$HOME/Library/Application Support/gogcli/credentials-work.json`

   Refresh token endpoint:
   `POST https://oauth2.googleapis.com/token` with `client_id`, `client_secret`, `refresh_token`, `grant_type=refresh_token`.

   Security: never print token/secret values. Delete the exported token file at the end:
   ```bash
   rm -f /tmp/sheets_work/work_token.json
   ```
4. Create scenario tabs with `spreadsheets.batchUpdate`:
   - `addSheet` for the new tab.
   - `values.update?valueInputOption=USER_ENTERED` for formulas and inputs.
   - `repeatCell` and `autoResizeDimensions` for formatting.
5. Make models formula-driven rather than fixed-value when asked:
   - Keep assumption/input cells near the top.
   - Pull source values from the existing source tab with formulas such as `INDEX(FILTER(...),1)`.
   - Monthly summaries should reference source monthly rows and calculate deltas from scenario inputs.
   - Include a `Change vs current model` column when comparing a scenario to an existing tab.
6. Verify by reading the resulting range back with `gog sheets get` and checking summary totals and month alignment. Watch for off-by-one errors caused by inserted blank rows.

## Formula-driven refactors of existing fixed-value models

When a user says a Sheets forecast/model tab is hard to maintain because values are copied or candidate names are used as keys:

1. Read the relevant ranges with formulas first:
   ```bash
   gog sheets get SPREADSHEET_ID "'Model tab'!A1:Z100" --account work --json --results-only --render FORMULA
   ```
   Also read the displayed values for verification after edits.
2. Identify which fields should remain editable inputs vs derived fields. For hiring models, candidate/display names often remain editable in the forecast tab, while role/function/start/comp/agency/variance/monthly summaries should be formulas.
3. Prefer stable helper keys over human names:
   - If a role is unique, use planned role as the key.
   - If planned role is duplicated, generate suffixes (`A`, `B`, `C`) with a helper formula such as:
     ```gs
     =IF(D18="","",D18&IF(COUNTIF($D$18:$D$31,D18)>1," "&CHAR(64+COUNTIF($D$18:D18,D18)),""))
     ```
   - Scenario tabs can then use `XLOOKUP(role_key, role_key_range, candidate_range)` to display candidate names without hardcoding them.
4. If the source workbook has a stable source-row/reference column, keep it as the mapping input and derive the rest with `INDEX(Source!col, source_row_offset)`. This lets formulas survive candidate-name changes while preserving explicit row mapping.
5. Convert copied summaries/breakdowns into formulas in dependency order:
   - Detail rows first (source-derived role/start/comp/agency/variance/helper keys).
   - Function summaries with `COUNTIF`/`SUMIF` over detail rows.
   - Monthly summaries with `FILTER` against start dates and month boundaries (`EOMONTH`).
   - Candidate monthly breakdowns by indexing detail rows and applying first-month vs ongoing variance.
6. Preserve model totals unless the user explicitly asks to change business logic. If direct source formulas expose decimals that were previously rounded (for example `$10,416.67` vs model `$10,417`), apply `ROUND(...,0)` or the existing model convention so scenario totals do not drift unexpectedly.
7. Always make a temporary JSON backup of ranges before broad formula conversion, then verify:
   - formulas are present in intended derived ranges (`--render FORMULA`),
   - displayed totals match expected prior totals (`--render FORMATTED_VALUE`),
   - no cells display `#...` errors,
   - linked scenario tabs still show aligned summaries.

## Headcount Budget vs Actual models

When maintaining headcount budget/actual Sheets tabs:

1. Prefer an internal `Opening ID` helper column in the source planning tab over row references or candidate/person names. For the FINN headcount workbook, the convention used was hidden `Headcount Planning!S:S` with header `Opening ID` and a note that it is an internal planning ID, not a Greenhouse ID.
2. Rewire target formulas with stable key lookups such as:
   ```gs
   XLOOKUP(id,'Headcount Planning'!$S:$S,'Headcount Planning'!$A:$A,"")
   ```
   Preserve the target table's opening order; only source-derived fields should look up by ID.
3. Budget monthly cost logic can use planned `Start Date`, falling back to `Estimate Start Date` when `Start Date` is text such as `ASAP`.
4. Actual/forecast monthly cost logic should use `Actual Start Date` if present, otherwise `Estimate Start Date`, and `Total Compensation (Actual)` for the monthly amount.
5. If the user asks for proration, scope it exactly to the requested table. In the FINN model the user requested proration only for `ACTUAL / FORECAST COSTS`: start month = `monthly comp / 30 * inclusive active days remaining in the month` (e.g. 26-Jun start = salary/30*5). Full later months remain full comp; if an end date exists, prorate the final month similarly.
6. Delta tables should generally remain `Actual / Forecast - Budget`; negative values are meaningful under-budget/unfilled variance, not errors. If the user wants a current candidate-only view, add a separate delta table that filters rows where `Prospective Candidate` or `Hired Candidate` is nonblank rather than changing the main delta.
7. For readability, delta table `Opening / mapped person` should mirror the `ACTUAL / FORECAST COSTS` display name (`Hired -> Role`, else `Prospective -> Role`, else `Unfilled -> Role`) when the user is reviewing candidate-level variances.
8. Always make a temporary JSON backup before broad formula edits, then verify formula wiring, displayed values, no `#...` errors, and that unrequested ranges did not change.

## Pitfalls

- `gog sheets get` returns displayed values by default; use `--render FORMULA` to distinguish fixed values from formulas. For verification after writes, read both formulas and displayed values: formulas confirm dependency wiring; displayed values catch `#...` errors and odd formatting.
- `gog sheets update --input USER_ENTERED` is enough for formulas in a range, but not for adding a tab or rich formatting.
- Date cells may display as currency if broad currency formatting overlaps assumption date cells. Apply date formatting after currency formatting.
- Do not key scenario formulas by candidate name when candidate names are the values users intend to edit. Use stable role/source keys and display candidate names through lookup formulas.
- When converting fixed-value models to formulas, do not formula-ize user-owned editable fields (e.g. candidate name overrides) unless the user explicitly requests it.
- When a user interrupts with a new scenario idea, stop immediately, avoid continuing verification, and summarize what was already read/written. For side-effecting spreadsheet work, explicitly say whether any sheet writes occurred.
