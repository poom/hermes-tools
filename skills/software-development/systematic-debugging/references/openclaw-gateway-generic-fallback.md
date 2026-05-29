# OpenClaw gateway generic fallback troubleshooting

Use this reference when a messaging user repeatedly receives:

```text
Something went wrong while processing your request. Please try again.
```

## What the message means

In OpenClaw's Telegram extension, this is a generic fallback emitted when message dispatch fails. It can be triggered by a failed agent run, delivery failure, or a higher-level dispatch exception. Do not treat the text itself as the root cause.

Known source locations from OpenClaw 2026.4.29:

```text
~/.openclaw/plugin-runtime-deps/openclaw-*/dist/extensions/telegram/*.js
~/.openclaw/plugin-runtime-deps/openclaw-*/dist/agent-runner.runtime-*.js
```

Search command:

```bash
grep -R "Something went wrong while processing your request" ~/.openclaw/plugin-runtime-deps ~/.openclaw/agents 2>/dev/null | head -20
```

## Fast evidence-gathering sequence

Run these before proposing fixes:

```bash
openclaw --version
openclaw status
openclaw health
openclaw gateway probe
ps aux | egrep -i 'openclaw|(^|/| )claw( |$)' | egrep -v 'egrep|grep'
lsof -nP -iTCP:18789 -sTCP:LISTEN 2>/dev/null || true
```

Check whether the TCP listener exists but the app is unresponsive:

```bash
python3 - <<'PY'
import socket, time
s=socket.socket(); s.settimeout(3)
t=time.time()
try:
    s.connect(('127.0.0.1',18789))
    print('tcp connect ok ms', round((time.time()-t)*1000))
except Exception as e:
    print('tcp connect fail', type(e).__name__, e)
finally:
    s.close()
PY
curl -sS --max-time 5 -I http://127.0.0.1:18789/ 2>&1 | head -40 || true
```

If TCP connects but HTTP/WebSocket health calls time out, the gateway process is alive but likely event-loop-stalled or CPU-bound.

## Log analysis patterns

Recent OpenClaw logs are usually under:

```text
~/.openclaw/logs/gateway.err.log
~/.openclaw/logs/gateway.log
```

Useful search:

```bash
grep -Ei 'dispatch failed|message processing failed|final reply failed|before_prompt_build handler from active-memory failed|CommandLaneTaskTimeoutError|SessionWriteLockTimeout|session-write-lock|liveness warning|Polling stall|sendMessage failed|sendChatAction failed|fetch timeout|closed before connect|embedded run failover decision' ~/.openclaw/logs/gateway.err.log | tail -100
```

Interpretation hints:

- `before_prompt_build handler from active-memory failed: timed out` + `CommandLaneTaskTimeoutError` means a hook/plugin is blocking prompt dispatch.
- `SessionWriteLockTimeoutError` or long `sessions.json.lock` releases indicate session store contention; repeated retries can amplify the stall.
- `liveness warning` with high `eventLoopDelay` / `eventLoopUtilization=1` / high CPU means the Node gateway is overloaded or wedged.
- `sendMessage failed` / `sendChatAction failed` can be downstream symptoms; verify Telegram API connectivity directly before assuming a network outage:

```bash
curl -sS --max-time 8 -I https://api.telegram.org 2>&1 | head -20
```

## Safe remediation order

1. Report evidence and ask before restarting if active runs may be interrupted.
2. If approved, restart only the OpenClaw gateway and verify:

```bash
openclaw gateway restart
openclaw health
openclaw status
```

3. If the gateway wedges again and logs repeatedly implicate `active-memory`, consider temporarily disabling or narrowing the `active-memory` plugin, then restart and re-test.
4. Avoid guessing from the generic Telegram text alone; use logs to identify whether the failure is agent/model timeout, delivery, session lock, plugin hook, or gateway liveness.
