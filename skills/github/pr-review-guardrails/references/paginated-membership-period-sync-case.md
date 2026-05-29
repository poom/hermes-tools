# Case study: membership-period sync consuming flat item-level pagination

Session source: review of `EWA-Services/Automated-Charging#1286` with linked producer `EWA-Services/Advance-Mgt-System#1098`.

Use this as an example pattern when a consumer replaces a full/grouped API response with a paginated endpoint for memory safety.

## Producer contract discovered

- New endpoint was additive; legacy full-response endpoints remained available for flag-off consumers.
- Paginated endpoint returned flat `data` plus `links`/`meta`, ordered by `membership_periods.id`.
- Because ordering/pagination was by membership-period row, one `user_id` could be split across pages.
- This was not a producer blocker by itself: flat item-level pagination was acceptable because grouping could be done by the consumer.

## Consumer behavior that made the PR approve-level

- Feature flag preserved the legacy full-response path when disabled.
- Flag-on path fetched pages with explicit `page`, `per_page`, and status/current filters rather than accidentally calling the full-table endpoint.
- The consumer staged every fetched page first, then loaded staged rows into a temporary table.
- Processing chunked distinct logical keys (`user_id`) using the configured chunk size, reloaded all staged rows for each user chunk, and only then ran the destructive per-user update.
- This avoided the common bug where page 2 deletes/replaces membership rows written from page 1 for the same user.
- Fetch failures on later pages aborted before applying staged data, avoiding partial sync.
- Response-size and missing-pagination-metadata guards prevented silent fallback to oversized/full-table behavior.
- Result/log samples were bounded so observability did not recreate the memory problem.

## Regression tests that mattered

Require or look for tests covering:

1. Memory-safe mode calls only the paginated endpoint and includes pagination/status parameters.
2. Same logical key appears on multiple pages; final parent/charge state includes all child rows from all pages.
3. Later-page failure produces no partial destructive apply.
4. Missing pagination metadata fails safely.
5. Oversized page/response body fails safely.
6. Flag-off path still uses the legacy endpoint/parser.
7. Configured chunk size is used for both staging inserts and distinct-key processing.
8. Command/cron exits non-zero when the handler fails.
9. Logs/results have bounded samples/counters.

## Review wording pattern

When the implementation is correct, the formal approval can say:

> The producer is a flat item-level paginator, so a user can span page boundaries. The consumer no longer assumes page-local completeness: it stages all page records, processes distinct users from the staged table, and groups all rows for each user before the destructive update. Regression coverage includes a same-user split across pages, later-page failure with no partial apply, pagination metadata fail-safe, and legacy flag-off behavior.

## Merge-readiness nuance

Separate code readiness from process/human gates. In this case, all technical checks passed and the review was approve-level, but GitHub remained blocked by stale human requested-changes / policy-bot disapproval. Report that as a process gate, not as a code blocker.
