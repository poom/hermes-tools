# OpenClaw Gateway CPU Pinned / Zombie Sessions (v2026.4.29)

Session-derived reference for diagnosing OpenClaw gateway pegging one CPU core and becoming unreachable after restarts.

## Symptom pattern

- OpenClaw gateway Node process (`openclaw/dist/index.js gateway --port 18789`) sits around 80–100% CPU.
- `openclaw status` may show the LaunchAgent running but gateway `unreachable (timeout)`.
- `openclaw gateway probe` reports `Connect: failed - timeout` even though process exists.
- `openclaw gateway stability` fails with `GatewayTransportError: gateway timeout after 10000ms`.
- Logs contain combinations of:
  - `liveness warning: reasons=event_loop_delay,event_loop_utilization,cpu`
  - `stuck session ... state=processing ... reason=processing_without_queue`
  - `stuck session recovery skipped: reason=active_embedded_run`
  - `SessionWriteLockTimeoutError: session file locked`
  - channel loops such as WhatsApp `status 408`, `Connection Terminated`, repeated auto-restarts.

## Related upstream issue

GitHub issue: `openclaw/openclaw#75707` — "Gateway CPU pinned at 100%: root causes & workarounds".

Relevant reported causes/workarounds:

- Persisted session files in `~/.openclaw/agents/*/sessions/*.jsonl` can relaunch embedded runs on gateway start.
- Compaction/session cleanup loops and session locks can compound gateway CPU saturation.
- Old sessions, large workspaces, plugin/channel startup loops, and per-message prep costs can all amplify CPU burn.
- Suggested workaround in the issue: purge or archive session artifacts; but do this only after a verified backup.

## Safe evidence sequence

1. Show process state:
   ```bash
   ps aux -r | head -15
   ps ax -o pid=,command= | grep 'openclaw/dist/index.js gateway --port 18789' | grep -v grep || true
   ```
2. Check OpenClaw health without changing state:
   ```bash
   openclaw status
   openclaw gateway probe
   openclaw gateway stability
   ```
3. Inspect recent logs for root-cause indicators:
   ```bash
   grep -E 'liveness warning|stuck session|SessionWriteLockTimeout|CommandLaneTaskTimeout|active-memory|GatewayTransportError|whatsapp|telegram' ~/.openclaw/logs/gateway.err.log | tail -80
   ```
4. If restarting, verify PID changed and wait at least 1–3 minutes while sampling CPU.
5. If CPU returns immediately after force-kill/restart and old sessions appear active, consider session cleanup.

## Critical backup rule before deleting session artifacts

Do **not** delete session files after a backup command merely exits/times out. Verify the backup first.

Preferred approach: backup only the session artifacts to keep the archive small and verifiable, instead of tarring the entire `agents/` directory (which may include huge workspaces/caches).

```bash
ts=$(date +%Y%m%d-%H%M%S)
backup_dir="$HOME/.openclaw/backups/session-cleanup-$ts"
mkdir -p "$backup_dir"

# Stop gateway first so sessions are not being written.
openclaw gateway stop || true
sleep 5

# Build a manifest of files that would be removed.
find "$HOME/.openclaw/agents" -path '*/sessions/*' \
  \( -name '*.jsonl' -o -name '*.jsonl.lock' -o -name 'sessions.json' -o -name 'sessions.json.lock' \) \
  -type f -print > "$backup_dir/manifest.txt"

# Archive exactly those files, preserving relative paths.
tar -czf "$backup_dir/session-artifacts.tar.gz" -C "$HOME/.openclaw" \
  $(sed "s|$HOME/.openclaw/||" "$backup_dir/manifest.txt")

# Mandatory verification before deletion.
gzip -t "$backup_dir/session-artifacts.tar.gz"
tar -tzf "$backup_dir/session-artifacts.tar.gz" >/dev/null
wc -l "$backup_dir/manifest.txt"
```

Only after the archive verifies successfully should deletion proceed:

```bash
while IFS= read -r f; do
  rm -f "$f"
done < "$backup_dir/manifest.txt"
```

Then restart and verify:

```bash
openclaw gateway start
sleep 30
openclaw status
openclaw gateway probe
openclaw gateway stability
```

## Pitfalls learned

- A tar of the entire `~/.openclaw/agents` can time out or be truncated because workspaces/caches are large. A truncated archive can still list/extract some files, but it is not a valid backup.
- Always run `gzip -t` and `tar -tzf` before any destructive action.
- If the user says to interrupt/stop and explain, stop tool loops and summarize; do not continue collecting more diagnostics.
- For user-facing incident response, prefer short status updates before long waits or multi-minute checks, especially after a destructive or risky step.
