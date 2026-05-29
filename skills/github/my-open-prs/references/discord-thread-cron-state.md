# Discord thread cron + durable PR state pattern

Session learning from installing the PR queue monitor for `discord:1505939375983427796`.

## Problem

The target Discord destination may be a normal channel, not a forum. A workflow that says "create one topic per PR" must not assume forum-post semantics. For a normal channel, create a Discord thread explicitly, then post the PR status into that thread.

## Confirm channel type

Resolve the channel directory with Hermes' venv Python if system Python is missing dependencies such as `yaml`:

```bash
cd "${HERMES_AGENT_DIR:-$HERMES_HOME/hermes-agent}"
./venv/bin/python - <<'PY'
from gateway.channel_directory import ChannelDirectory
cd = ChannelDirectory()
for name in ["1505939375983427796", "#my-open-prs", "my-open-prs"]:
    resolved = cd.resolve(name)
    print(name, "=>", resolved)
PY
```

If the result type is `channel`, use explicit thread creation. If the result type is `forum`, direct forum-post behavior may be available, but explicit threads are still safer when supported.

## Correct create-topic sequence for normal Discord channels

1. Generate actions:

```bash
python3 scripts/my_open_prs.py --actions-json
```

2. For each `create_topic` action:

```text
discord(action='create_thread', channel_id='1505939375983427796', name=action.topic_title)
send_message(action='send', target='discord:1505939375983427796:<thread_id>', message=action.message)
python3 scripts/my_open_prs.py --mark-posted --repo '<repo>' --number <n> --signature '<sig>' --kind update --thread-id '<thread_id>' --message-id '<message_id>'
```

Only mark posted after the Discord operation succeeds. If thread creation succeeds but no `thread_id` is returned, do not mark posted; future updates would not know where to go.

## Cron job shape

- Use an LLM cron job, not `no_agent`, because it needs to call Discord/message tools and then mark state.
- Delivery should be `local`.
- Toolsets should include `terminal`, `file`, `messaging`, and `discord`.
- Return `[SILENT]` when there are no actions or all user-visible posts already went to Discord.

## State/backup coupling

Durable PR status files belong under:

```text
$HERMES_HOME/my-open-prs
```

The Hermes config backup script should include `my-open-prs/` alongside `skills`, `scripts`, `hooks`, and `bin`, then run its existing secret scan/sanitization before commit/push. This preserves `thread_id`, `message_id`, last posted signatures, stale ping timestamps, and closed-post markers across restores.
