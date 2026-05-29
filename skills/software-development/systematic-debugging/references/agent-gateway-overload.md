# Agent Gateway Overload / Generic Messaging Fallbacks

Session-derived reference for debugging local agent gateways (OpenClaw/Hermes-like) that return generic chat errors such as:

> Something went wrong while processing your request. Please try again.

## Key learning

A gateway process can be alive and listening on its port while its event loop/application layer is wedged. In this state:

- TCP connect succeeds.
- CLI status may report the service/LaunchAgent is loaded.
- Health/probe calls time out.
- The messaging adapter sends a generic fallback because dispatch failed.
- CPU may sit around one full core, with logs showing event-loop delay and command-lane timeouts.

Do not stop at “process is running.” Verify responsiveness.

## Evidence pattern from OpenClaw

Observed symptoms:

```text
Gateway: ws://127.0.0.1:18789 · unreachable (timeout)
GatewayTransportError: gateway timeout after 10000ms
Reachable: no
Connect: failed - timeout
```

Process state:

```bash
ps aux -r | head -15
ps -o pid,ppid,%cpu,%mem,rss,etime,stat,command -p <pid>
lsof -nP -iTCP:<port> -sTCP:LISTEN
```

Important distinction:

```text
TCP connect ok 127.0.0.1 18789
curl: Operation timed out with 0 bytes received
```

That means the listener exists but the app is not serving responses.

Common log lines in this failure mode:

```text
[diagnostic] liveness warning: reasons=event_loop_delay,event_loop_utilization,cpu
[plugins] [hooks] before_prompt_build handler from active-memory failed: timed out after 35000ms
CommandLaneTaskTimeoutError: Command lane "main" task timed out after 35000ms
SessionWriteLockTimeoutError: session file locked
[telegram] message processing failed: HttpError: Network request for 'sendMessage' failed!
[telegram] Polling stall detected
[ws] closed before connect ... code=1006
```

## Safe triage sequence

1. **Show the high-CPU process first if the user asks.** Do not restart before confirming what is consuming CPU.

   ```bash
   ps aux -r | head -15
   ps aux | egrep -i 'openclaw|hermes|node' | egrep -v 'egrep|grep' | sort -k3 -nr | head -30
   ```

2. **Verify the gateway process, service, and port.**

   ```bash
   pgrep -af 'openclaw/dist/index.js gateway --port 18789' || true
   launchctl list | grep -i openclaw || true
   lsof -nP -iTCP:18789 -sTCP:LISTEN || true
   ```

3. **Probe application responsiveness, not just TCP.**

   ```bash
   openclaw status
   openclaw health
   openclaw gateway probe
   curl -sS --max-time 5 -I http://127.0.0.1:18789/ || true
   ```

4. **Inspect recent logs for root cause before changing config.**

   ```bash
   grep -E 'active-memory failed|CommandLaneTaskTimeoutError|SessionWriteLockTimeoutError|sendMessage failed|message processing failed|final reply failed|liveness warning|Polling stall|fetch-timeout|GatewayTransportError|closed before connect|agent cleanup timed out' <home>/.openclaw/logs/gateway.err.log | tail -80
   ```

5. **Restart the gateway service when it is wedged.** Prefer the product command once the CLI is responsive:

   ```bash
   openclaw gateway restart
   ```

   On macOS this restarts LaunchAgent `gui/$(id -u)/ai.openclaw.gateway`. Verify the PID changed:

   ```bash
   old=<old-pid>
   openclaw gateway restart
   sleep 10
   pgrep -af 'openclaw/dist/index.js gateway --port 18789'
   ```

6. **Wait a few minutes and recheck.** Startup can temporarily use high CPU/RSS.

   ```bash
   for s in 30 60 90 120 150; do
     sleep 30
     pid=$(pgrep -f 'openclaw/dist/index.js gateway --port 18789' | head -1 || true)
     [ -n "$pid" ] && ps -o pid,%cpu,%mem,rss,etime,stat -p "$pid"
   done
   openclaw status --deep
   openclaw health
   openclaw gateway probe
   openclaw gateway stability
   ```

7. **Only disable suspect plugins if restart does not recover.** In the observed case, active-memory produced timeouts before restart, but the gateway recovered after restart and active-memory stayed enabled. Do not disable it preemptively.

## Expected recovered state

Healthy enough after restart:

```text
Gateway: reachable <latency>
Gateway service: running (new pid)
Tasks: 0 active · 0 queued · 0 running
Telegram: OK
WhatsApp: LINKED
CPU: <1% after stabilization
```

A probe warning like this can remain while status/health are OK:

```text
Gateway accepted the WebSocket connection, but follow-up read diagnostics failed: timeout
```

Treat it as a warning, not immediate failure, if `status --deep`, `health`, and message delivery are otherwise OK.

## Post-restart relapse pattern: stuck cron/subagent sessions

A restart can succeed at the service level (new PID, channels start, stale `.lock` files removed) but still relapse into high CPU within minutes if persisted sessions are reloaded and a cron/subagent run remains logically active.

Evidence pattern:

```text
OpenClaw PID before restart: 51476
Restarted LaunchAgent: gui/501/ai.openclaw.gateway
OpenClaw PID after restart: 54817
[gateway] ready
[gateway] removed stale session lock: ...jsonl.lock (dead-pid, too-old)
[diagnostic] liveness warning: reasons=event_loop_delay,event_loop_utilization,cpu
[diagnostic] stuck session ... state=processing ... reason=processing_without_queue
[diagnostic] stuck session recovery skipped: reason=active_embedded_run action=observe_only
SessionWriteLockTimeoutError: session file locked ... sessions.json.lock
Gateway: local · ws://127.0.0.1:18789 · unreachable (timeout)
GatewayTransportError: gateway timeout after 10000ms
```

The key clue is that `openclaw status` may show `0 active · 0 queued · 0 running` tasks while the session table still contains recent `agent:main:cron:<id>` and `agent:main:subagent:<id>` entries, and logs report stuck sessions with `active_embedded_run`. Treat this as a persisted-session/cron relapse, not a failed LaunchAgent restart.

Useful read-only checks after a relapse:

```bash
openclaw status 2>&1 | tail -120
openclaw gateway probe 2>&1 | tail -60
openclaw gateway stability 2>&1 | tail -80
python3 - <<'PY'
from pathlib import Path
import re
p = Path.home()/'.openclaw/logs/gateway.err.log'
pat = re.compile(r'stuck session|active_embedded_run|SessionWriteLockTimeout|CommandLaneTaskTimeout|liveness warning|agent/embedded|GatewayTransportError', re.I)
for line in [l for l in p.read_text(errors='replace').splitlines() if pat.search(l)][-80:]:
    print(line)
PY
```

When reporting this to the user, separate:

- **Service restart result:** old PID, new PID, LaunchAgent state.
- **Relapse evidence:** CPU samples over a bounded window, gateway/probe timeouts, stuck session keys.
- **Next action needs approval:** pausing/removing the offending cron, clearing session locks/state, disabling plugins, or restarting again are side-effecting actions.

## Operator communication pitfall

For live production-ish agent gateways, don't silently continue long verification after the requested side effect. After `openclaw gateway restart`, immediately report the restart result if the user asks what is happening or if the next step will take more than ~30-60 seconds. Then either stop for approval or state a bounded sampling plan (for example, “I’ll sample CPU for 2 minutes and not change anything”).

## Pitfalls

- Do not interpret generic Telegram fallback text as the root cause; it is often just a dispatch wrapper.
- Do not assume a running process or open port means the gateway is healthy.
- Do not assume a successful restart fixed the fault; persisted cron/subagent sessions can immediately re-wedge the gateway.
- Do not run long all-in-one restart/wait/check scripts if the tool environment may time out; split into bounded steps.
- Do not disable plugins, pause cron jobs, delete locks, or clear sessions before checking whether a clean service restart resolves stale locks/event-loop stalls and getting approval for side effects.
