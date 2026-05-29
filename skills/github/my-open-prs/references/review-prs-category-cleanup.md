# review-prs category cleanup notes

Use this when the user says the `review-prs` Discord category has too many PR channels or closed/merged PR channels were not removed.

## Key distinction

There are two different cleanup patterns:

- **Discord threads under a parent channel**: scripts like `<home>/.hermes/scripts/discord_pr_thread_closer.py` call `/guilds/<guild>/threads/active` and archive threads. They do not see or delete normal text channels under a category.
- **Normal text channels under a Discord category**: current PR review routing uses one normal text channel per PR under categories like `review-prs`, `pr-waiting-for-approval`, `pr-need-actions`, and `pr-waiting-for-checks`. These must be enumerated from `/guilds/<guild_id>/channels` and filtered by `parent_id`.

If the user reports “a lot of channels,” first check whether the active cron job is a **thread** closer. If so, it can be healthy and still leave stale text channels behind.

## Safe audit workflow

1. Identify the Discord server/guild and the category named `review-prs`.
2. List all child channels where `type == 0` and `parent_id == <review-prs-category-id>`.
3. Skip hub/summary channels such as `prs` unless the user explicitly asks to audit them.
4. For each PR channel, fetch recent messages and embeds and extract the canonical GitHub PR URL: `https://github.com/<owner>/<repo>/pull/<number>`.
5. Verify live status with GitHub, e.g. `gh api repos/<owner>/<repo>/pulls/<number> --jq '{state:.state, merged:.merged, closed_at:.closed_at, merged_at:.merged_at, title:.title, html_url:.html_url}'`.
6. Classify into `closed_or_merged`, `open`, `unknown`, and `errors`.
7. Report counts and the stale channel names before deleting anything.

## Deletion guardrail

Deleting normal Discord text channels is destructive. Do not delete or enable an auto-delete cron job until the user explicitly approves that scope. A good interim response is: “I found N stale PR text channels; I did not delete anything. Say go and I’ll delete those N / install an auto-delete job.”

## Cron remediation pattern

If the user wants ongoing cleanup, implement a deterministic no-agent cron job specifically for PR **text channels**, not thread archival. It should:

- enumerate Discord guild channels under the relevant PR categories by `parent_id`;
- extract/verify GitHub PR URLs from channel content/topic before deletion;
- delete only when PR state is closed or merged;
- stay silent on no-op runs;
- print a compact one-message summary like `<channel name> - deleted` when it deletes channels;
- keep closed/open/unknown/error counters in local state for troubleshooting.

Do not mistake an existing `discord_pr_thread_closer.py` job as sufficient coverage for normal text channels.
