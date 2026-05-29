# Discord per-PR text channels

Session-derived workflow for `my-open-prs` monitor mode.

## User correction

Threads in the parent status channel (`<#1505939375983427796>`) make the channel messy. Prefer one normal Discord text channel per active PR instead of threads or forum posts.

## Pattern

- Treat `1505939375983427796` as the stable source/parent status channel.
- Create each PR channel in the same guild/category as that source channel.
- Use deterministic names: `<repo>-pr-<number>` (lowercase, Discord-safe, e.g. `finn-web-app-pr-4970`).
- Store the returned `channel_id` in the per-PR Markdown status record under `<home>/.hermes/my-open-prs`.
- Send subsequent blocker/status updates to `discord:<channel_id>`.
- When a PR is merged/closed, post the final merged/closed notice to the parent status channel, delete the PR text channel, then mark the closed action posted.

## Tooling notes

Hermes' built-in Discord tool had thread support but not normal channel create/delete. The skill therefore uses `scripts/discord_pr_channels.py`, which talks to Discord REST with `DISCORD_BOT_TOKEN` from the environment or `<home>/.hermes/.env`.

Safety checks in the helper:

- `create` fetches the source channel first and reuses its guild/category. If a legacy `pr-<repo>-<number>` channel exists for the requested `<repo>-pr-<number>` name, `create` adopts and renames it instead of creating a duplicate.
- `delete` refuses to delete the source channel.
- `delete` refuses non-text channels.
- `rename` refuses the source channel, non-text channels, and unmanaged current names unless forced.
- `delete` refuses text channels whose name is not a managed PR channel name (`<repo>-pr-<number>` or legacy `pr-<repo>-<number>`) unless forced.

## Verification recipe

Before relying on cron after changes, run a reversible smoke test:

```bash
created=$(python3 scripts/discord_pr_channels.py create \
  --source-channel-id 1505939375983427796 \
  --name hermes-test-pr-1 \
  --topic 'Temporary Hermes my-open-prs create/delete smoke test')
channel_id=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["channel_id"])' <<<"$created")
python3 scripts/discord_pr_channels.py delete \
  --source-channel-id 1505939375983427796 \
  --channel-id "$channel_id"
```

Then verify actions are clean after processing:

```bash
python3 scripts/my_open_prs.py --actions-json
```

Expected steady state: `"actions": []`.
