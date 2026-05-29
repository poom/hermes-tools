# Resolver Cases

Route to `pending-pr-review-github-issues-queue` when the request mentions:

- distributed pending PR review queue
- GitHub Issues queue for PR reviews
- coordinator or worker for Poom's pending reviews
- posting, queueing, or adding a PR URL to the review board
- claim comments, leases, heartbeats, or stale sweep
- `poom/hermes-pr-review-queue`
- avoiding duplicate reviews across Mac and Ubuntu Hermes machines

Do not route here for:

- a single PR review URL without queue setup language;
- a normal "review my pending PRs" request that should run `pending-pr-review`;
- general GitHub issue triage unrelated to the Hermes review queue.

Example positives:

- "Set up the GitHub Issues queue for pending PR review workers."
- "Why did two workers race on the same queue issue?"
- "Run the coordinator dry-run for poom/hermes-pr-review-queue."
- "Requeue stale claimed PR review tasks."
- "Post https://github.com/EWA-Services/user-iam/pull/201 to the board."
- "Queue EWA-Services/user-iam#201 for Poom review."

Example negatives:

- "Review https://github.com/EWA-Services/finn-web-app/pull/4974."
- "What PRs are waiting for me?"
- "Summarize my authored open PRs."
