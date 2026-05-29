# Learn preload / impression attribution PR case

Use this reference when reviewing a frontend PR that preloads Learn/Financial Education content from a page that is itself part of an experiment funnel, and prior review comments objected that the preload uses a tracked article-detail endpoint.

## Key distinction

Separate two questions before deciding whether to block:

1. **Impression vs click semantics** — Does product/analytics intentionally count the card render/preload as an impression-level conversion for this entry point?
2. **Duplicate conversion on actual open** — If the user taps the card after the preload, does the article detail page issue a second tracked slug/detail request for the same article?

If the author/product explicitly accepts impression-level attribution for the current ticket, do not keep blocking solely because the preload is tracked. Treat strict click-only semantics or an untracked eligibility/existence endpoint as a follow-up unless the ticket/experiment policy requires click-only metrics.

Still block if the code double-counts the same user journey: preload calls the tracked endpoint, then article detail calls the same tracked endpoint again when the user opens the article.

## Evidence pattern that unblocks the double-count concern

Approve-level evidence looks like:

- Source page sets a source/entry-point signal before the tracked preload and restores it afterward.
- The preload stores the article in a one-time handoff cache keyed by both slug and source/entry point.
- The article detail page first tries to consume the matching handoff and returns before calling the tracked `getArticleBySlug` fallback.
- Tests assert the prefetched path skips `getArticleBySlug` and that the handoff is consumed once and only when slug/source match.

## Review wording

Suggested non-blocking follow-up language:

> If FINN wants strict click-only Financial Education conversion semantics, add a separate untracked Learn eligibility/existence path and update the analytics contract in a follow-up. I am not blocking this rollout on that broader contract change because the current implementation now avoids duplicate conversion tracking for actual article opens.

## Concrete case

FINN-Web-App #4949 (FE-2508) had an author clarification that one tracked Financial Education preload/impression from the Advance Unavailable page was an intentional product/analytics decision. Current head added a source-scoped prefetched-article handoff consumed by `ArticleDetailPage` before the tracked slug fallback, so the earlier duplicate-conversion blocker became stale and the PR was approved.
