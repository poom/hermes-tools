# Preserved My Open PRs Guide

This reference preserves the previous detailed operating guide. Use it for step-by-step procedures after the lean `SKILL.md` routes to this skill.

## Previous Frontmatter

```yaml
name: my-open-prs
description: Use when tracking the current user's open non-draft GitHub pull requests in ewa-services, posting a PR queue summary to Discord, creating one normal Discord text channel per active PR, keeping per-PR blocker/status channels up to date, reporting merged/closed PRs, deleting the PR channel when closed/merged, and maintaining durable per-PR Markdown status files under <hermes-home>/my-open-prs.
required-skills: []
required-binaries:
  - gh
  - python3
```

## Previous Operating Guide

# My Open PRs

## Overview

Use this skill to report and monitor the user's open PR queue in `ewa-services`.
The default search is:

```text
is:open is:pr author:@me archived:false org:ewa-services draft:false
```

The skill supports two operator modes:

1. **Show summary now**: print a grouped Markdown report in chat.
2. **Monitor/post mode**: persist one Markdown status file per PR, emit Discord post actions only when something changed, create one normal Discord text channel per active PR, post blocker updates in that PR channel, post merged/closed status in the parent Discord channel, delete the PR channel after close/merge, and ping the user after 24h of no GitHub activity.

Default Discord parent channel:

```text
discord:1505939375983427796
```

Status files live at:

```text
<hermes-home>/my-open-prs/<owner>-<repo>-pr-<number>.md
```

Each file is Markdown with a `my-open-prs` JSON metadata comment, so it is readable by humans and deterministic for scripts.

## When to Use

- The user asks for their PR queue, open PR status, review blockers, merge blockers, or "why my PR did not merge".
- The user asks to post PR status to `<#1505939375983427796>`.
- The user asks for one channel/topic/thread per PR, PR blocker updates, merged/closed announcements, deleting closed PR channels, or stale/no-activity pings.
- A cron job needs to run hourly and post only when a PR's tracked status changed.

Don't use this for reviewing somebody else's PRs or formal GitHub review submissions; use `pending-pr-review` or `pr-review-guardrails` for those workflows.

## Show Summary Workflow

Run from this skill directory:

```bash
python3 scripts/my_open_prs.py
```

Useful options:

```bash
python3 scripts/my_open_prs.py --include-empty
python3 scripts/my_open_prs.py --query 'is:open is:pr author:@me archived:false org:ewa-services draft:false repo:ewa-services/example'
python3 scripts/my_open_prs.py --json
```

Present the script's Markdown output directly unless the user asks for a different grouping or detail level.

If an item in `Needs My Feedback` has only a generic reason, inspect that PR with `gh pr view`, `gh pr checks`, or `gh api` and replace the generic reason with a short actionable summary backed by GitHub evidence. In particular, do not treat GitHub `mergeStateStatus=BLOCKED` as author feedback by itself: when the PR is approved but blocked by pending `policy-bot` / outstanding `reviewRequests`, classify and explain it as `Waiting on Review` instead. Also do not use GitHub `updatedAt` alone as a Discord update trigger: bot comments/check reruns change `updatedAt` and cause duplicate same-status alerts. Only bucket/blocker/material PR state changes should alter `Entry.signature`. See `references/classification-pitfalls.md` (`references/classification-pitfalls.md`).

## Monitor/Post Workflow

Run the deterministic action generator:

```bash
python3 scripts/my_open_prs.py --actions-json
```

It writes/updates per-PR status files and emits JSON like:

```json
{
  "actions": [
    {
      "type": "create_channel",
      "target": "discord:1505939375983427796",
      "repo": "EWA-Services/web",
      "number": 12,
      "signature": "abc123...",
      "channel_name": "web-pr-12",
      "message": "web #12 Improve checkout\n\n..."
    }
  ]
```

Continuation:

```json
}
```

Action semantics:

- `create_channel`: Run `python3 scripts/discord_pr_channels.py create --source-channel-id 1505939375983427796 --name <action.channel_name> --category-name <action.category_name>`. The helper is idempotent: it first searches the guild for an existing same-name text channel or legacy `pr-<repo>-<number>` alias, reuses/adopts/renames it instead of creating a duplicate, and moves it into the bucket category. Then send `message` into `discord:<channel_id>` with `send_message` and record the returned `channel_id`.
- `post_update`: Before sending, run `python3 scripts/discord_pr_channels.py move --source-channel-id 1505939375983427796 --channel-id <action.channel_id> --category-name <action.category_name>` so bucket changes move the channel to the correct Discord category. Then send `message` to the PR channel target (`discord:<channel_id>`) because bucket/blocker/status changed.
- `ping_stale`: Optionally run the same `move` command if `action.category_name` is present, then send `message` to the PR channel target because GitHub `updatedAt` has had no activity for more than 24 hours and there has not been another stale ping in the last 24 hours.
- `post_closed`: Send `message` to the parent channel because a previously tracked open PR is now merged/closed, then delete the PR text channel with `python3 scripts/discord_pr_channels.py delete --source-channel-id 1505939375983427796 --channel-id <action.channel_id>`. Only mark closed after both the parent notice and channel deletion succeed.

After each successful send, mark the action posted so the next hourly run stays silent unless something changes:

```bash
python3 scripts/my_open_prs.py --mark-posted \
  --repo EWA-Services/web \
  --number 12 \
  --signature abc123 \
  --kind update
```

For a newly created Discord PR channel, also record the channel ID returned by `discord_pr_channels.py create` and the message ID returned by `send_message` when available:

```bash
python3 scripts/my_open_prs.py --mark-posted \
  --repo EWA-Services/web \
  --number 12 \
  --signature abc123 \
  --channel-id 1234567890123456789 \
  --message-id 9876543210987654321 \
  --kind update
```

For `ping_stale`, use `--kind stale`. For `post_closed`, use `--kind closed`.

## Cron Job Pattern

Use an LLM cron job (not `no_agent`) with `deliver: local`, because the job must dynamically send to the parent channel or individual PR channels and then record post acknowledgements.

Prompt skeleton:

```text
Load/use the my-open-prs skill. Run:
python3 <home>/.hermes/skills/github/my-open-prs/scripts/my_open_prs.py --actions-json

If actions is empty, respond exactly [SILENT].
For each action, use tools to deliver it:
- For `create_channel`, run `python3 scripts/discord_pr_channels.py create --source-channel-id 1505939375983427796 --name <action.channel_name> --category-name <action.category_name>`; the helper may return `action: "reuse"` if a same-name channel already exists. Parse `channel_id`, then send `action.message` to `discord:<channel_id>` with `send_message`.
- For `post_update` and `ping_stale`, if `action.channel_id` and `action.category_name` are present, first run `python3 scripts/discord_pr_channels.py move --source-channel-id 1505939375983427796 --channel-id <action.channel_id> --category-name <action.category_name>`, then call send_message(action='send', target=action.target, message=action.message).
- For `post_closed`, call send_message(action='send', target=action.target, message=action.message), then if `action.channel_id` is present run `python3 scripts/discord_pr_channels.py delete --source-channel-id 1505939375983427796 --channel-id <action.channel_id>`.
Only if the Discord operation succeeds, run --mark-posted with the action repo/number/signature/kind.
For create_channel, also pass returned channel_id and message_id when available. For post_closed with a channel_id, only mark posted after deletion succeeds. If a send/delete fails, do not mark it posted; include the failure in the final local-only response.
After processing all actions, respond [SILENT] if every successful post already went to Discord and there were no failures.
```

Recommended cron settings:

- Schedule: `every 1h`
- Deliver: `local`
- Toolsets: `terminal`, `file`, `messaging`
- Workdir: `$HERMES_HOME/skills/github/my-open-prs`

## Discord Category Buckets

Use Discord categories as the visible status indicator. Keep PR channel names stable as `<repo>-pr-<number>` (for example `finn-web-app-pr-4970`); do not add an `h-` or leading `pr-` prefix when categories are enabled.

Bucket-to-category mapping:

- `Waiting on Review` → `pr-waiting-for-approval`
- `Needs My Feedback` → `pr-need-actions`
- `Waiting on Checks / Merge` → `pr-waiting-for-checks`

When a PR bucket changes, move the existing PR channel to the corresponding category with:

```bash
python3 scripts/discord_pr_channels.py move \
  --source-channel-id 1505939375983427796 \
  --channel-id <channel_id> \
  --category-name <category_name>
```

`discord_pr_channels.py create` also accepts `--category-name`; it creates/reuses that category and adopts/moves any existing same-name PR channel or legacy `pr-<repo>-<number>` alias instead of creating a duplicate. To manually rename a managed PR channel, use `python3 scripts/discord_pr_channels.py rename --source-channel-id 1505939375983427796 --channel-id <channel_id> --name <repo>-pr-<number>`.

## Default Headings

Use these names unless the user requests different wording:

- `Waiting on Review`: no detected author action; the PR needs reviewer approval or reviewer attention.
- `Waiting on Checks / Merge`: no detected author action; checks, merge queue, or a manual merge is still pending.
- `Needs My Feedback`: changes requested, failing checks, merge conflicts, stale branch, or another blocker the author likely needs to address.

Omit empty sections unless the user asks for a complete report.

## Legacy/Untracked PR Channels

Some older PR channels may not appear in `<home>/.hermes/my-open-prs/*.md` because they were created by the legacy `gh-pr-queue` flow. These commonly use lowercased names like `pr-<repo-name>-<pr-number>` (for example `pr-ewa-actions-425`) and have topics like `EWA-Services/<Repo> #<number> — managed by Hermes gh-pr-queue`. Current `my-open-prs` channels use `<repo>-pr-<number>`.

When the user points to a specific Discord channel that is not found in status files:

1. Fetch Discord channel metadata with `discord_pr_channels.get_channel()` (or an equivalent Discord API GET) and inspect `name` and `topic`.
2. Map topic/name to `owner/repo` and PR number.
3. Verify the live PR state with `gh pr view <number> --repo <owner>/<repo> --json number,state,closed,closedAt,mergedAt,title,url,updatedAt`.
4. If the PR is `CLOSED`/`MERGED`, delete the specified channel directly with `python3 scripts/discord_pr_channels.py delete --source-channel-id 1505939375983427796 --channel-id <channel_id>`.
5. Verify deletion by re-running the delete or GET; `404 Unknown Channel` confirms it is gone.

Do not rely only on the current status file's `channel_id`; legacy duplicate channels can exist for the same PR.

When the user reports many legacy/duplicate channels:

1. List all text channels in the same category as source channel `1505939375983427796`.
2. Classify PR channels by topic:
   - legacy: topic contains `managed by Hermes gh-pr-queue`
   - current: topic contains `Managed by Hermes my-open-prs`
3. For each legacy channel, parse `EWA-Services/<repo> #<number>` from the topic and verify the PR with `gh pr view`.
4. If a current `my-open-prs` channel exists with the same channel name, delete the legacy duplicate even if the PR is still open; keep the current tracked channel.
5. If no current channel exists, only delete the legacy channel when the PR is `CLOSED` or `MERGED`; otherwise report it rather than deleting.
6. Re-scan the category afterward and report `legacy_count` and `current_count`.

When the user says the `review-prs` category itself has a lot of channels, do not assume the existing Discord PR **thread** closer handles it. Thread closers only archive active Discord threads under a parent channel; normal per-PR text channels under a category must be listed via guild channels filtered by `parent_id`. Audit the category, extract GitHub PR URLs from each channel's recent messages/embeds, verify live PR state with GitHub, and report stale channel names/counts before deleting anything. See `references/review-prs-category-cleanup.md` (`references/review-prs-category-cleanup.md`).

## Failure Behavior

- If `gh` is missing or not authenticated, report the exact command failure and ask the user to run `gh auth login` or provide GitHub access.
- If live PR details cannot be fetched, stop instead of inventing status.
- If `send_message` fails, do not run `--mark-posted`; this makes the next cron run retry the action.
- If `discord_pr_channels.py create` succeeds but the output lacks `channel_id`, report the problem and do not mark posted, because future updates would not know where to post.
- If `discord_pr_channels.py delete` fails for a closed/merged PR, do not mark the closed action posted; the next cron run should retry the parent notice + deletion.
- If a `Needs My Feedback` reason is generic after script output, inspect the PR and summarize only evidence present in GitHub.

## References

- `references/discord-thread-cron-state.md` (`references/discord-thread-cron-state.md`) - historical pattern for normal Discord channels using explicit threads; this skill now prefers one normal text channel per PR to avoid making the parent status channel messy.
- `references/discord-pr-text-channels.md` (`references/discord-pr-text-channels.md`) - current per-PR normal text channel pattern, create/delete helper safety checks, and reversible Discord smoke test.
- `references/classification-pitfalls.md` (`references/classification-pitfalls.md`) - classification edge cases, especially why `mergeStateStatus=BLOCKED` can mean waiting on policy/reviewer approval rather than author feedback.
- `references/review-prs-category-cleanup.md` (`references/review-prs-category-cleanup.md`) - audit/remediation pattern for stale normal text channels under the `review-prs` category, including the pitfall that Discord thread closer jobs do not cover category child channels.

## Verification Checklist

- [ ] `python3 scripts/test_my_open_prs.py` passes.
- [ ] `python3 scripts/my_open_prs.py --from-json 09-e2e-smoke/sample_payload.json --actions-json --status-dir <tmp> --no-fetch-closed` emits deterministic actions.
- [ ] Each generated Markdown status file has a `my-open-prs` metadata comment and readable PR status summary.
- [ ] A successful `create_channel` action is followed by `--mark-posted --channel-id <id>`.
- [ ] The hourly cron job uses `deliver: local` and only posts to Discord when `actions` is non-empty.
