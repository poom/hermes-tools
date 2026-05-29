# Paginated API producer/consumer contract reviews

Use when a PR changes a producer API and a linked consumer PR adopts it, especially when the old API returned grouped data and the new API returns flat paginated records.

See also `references/paginated-membership-period-sync-case.md` for a concrete approve-level case where a consumer made item-level pagination memory-safe by staging all pages, chunking distinct logical keys, and regrouping before destructive updates.

## Review pattern

1. Inspect both PRs before deciding which repo owns the blocker:
   - Producer endpoint query shape, ordering, response shape, and pagination metadata.
   - Producer tests that reveal contract boundaries (e.g. `per_page=1`, repeated users, duplicated grouping keys).
   - Consumer staging/streaming/apply logic and whether it assumes grouped or atomic records.
2. Identify the pagination unit explicitly:
   - item-level pagination: a logical group/user/account may span pages.
   - group-level pagination: all records for a logical group are guaranteed to stay together.
3. If the producer returns a flat item-level paginator, do not invent an implicit grouping guarantee. Treat cross-page aggregation as a consumer responsibility unless the API contract/ticket explicitly requires grouped pagination.
4. In the consumer, look for per-page processing that calls destructive/idempotency-sensitive code per group:
   - deletes/replaces existing child rows for a parent/charge/request
   - overwrites subtotal/aggregate fields
   - marks a group processed before all pages are read
   - emits success after each page rather than after a whole logical group
5. Require a regression test where the same logical key appears on multiple pages. Assert all child rows survive and aggregate totals include the cross-page sum.

## Common blocker wording

> The new producer endpoint is a flat item-level paginator, so the same `<group_key>` can appear on multiple pages. The consumer currently groups only within each staged page and runs the destructive per-group update once per page. If a group appears on page 1 and page 2, page 2 can delete/overwrite rows or subtotals written from page 1. Please aggregate/stage by `<group_key>` across all fetched pages, or make the per-group update merge idempotently across pages, and add a regression test with the same group split across pages.

## Evidence to collect

- Producer: route/controller/service lines showing flat `data`, `meta`, `links`, order-by, and `paginate(...)` call.
- Producer tests proving or permitting cross-page split (e.g. same user with multiple rows and `per_page=1`).
- Consumer: page fetch loop, staging file layout, `groupBy(...)`, destructive delete/insert/overwrite logic, and missing split-key test.
- CI/local test limitations, if any, clearly separated from code evidence.
