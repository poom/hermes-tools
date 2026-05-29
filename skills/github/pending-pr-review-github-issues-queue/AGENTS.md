# Resolver routing

Use this skill when Poom asks to set up, operate, test, or debug the distributed
pending PR review queue backed by GitHub Issues, or when Poom provides a PR URL
and asks to post/queue/add it to the review board.

Do not use this skill for a direct review of a single PR. Route single PR
reviews to `pr-review-guardrails`, and route simple local batch review requests
to `pending-pr-review` unless the request specifically involves the shared
GitHub Issues queue.
