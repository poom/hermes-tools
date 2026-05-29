# OpenClaw v2026.5.2 native Codex runtime recovery

Use this when OpenClaw is upgraded and ChatGPT/Codex subscription routing or native Codex runtime breaks.

## Symptom clusters

- Gateway reachable but high CPU/event-loop delay; `openclaw gateway probe` times out or is slow.
- Model routing was changed from `openai-codex/gpt-*` to `openai/gpt-*` and errors now mention native Codex harness.
- Errors observed:
  - `Requested agent harness "codex" is not registered and PI fallback is disabled.`
  - `plugins.entries.codex: plugin not found: codex`
  - `ConfigMutationConflictError: config changed since last load` during plugin install.
  - After plugin registration: `Codex agent harness failed; not falling back to embedded PI backend` and `codex app-server startup aborted`.
- Logs may also show old `openai-codex` timeouts, `llm-idle-timeout`, active-memory hook timeouts, queued Telegram/direct work, and `diagnostic.liveness.warning`.

## Key distinction

OpenClaw v2026.5.2 docs distinguish two routes:

- ChatGPT/Codex subscription native runtime: `openai/gpt-*` with `agents.defaults.agentRuntime.id = "codex"`.
- PI OAuth route: `openai-codex/*`.

Do not assume personal Codex CLI login is enough for OpenClaw. Verify both:

```bash
codex --version
codex auth status 2>&1 || codex login status 2>&1 || true
timeout 60 codex exec -m gpt-5.5 --skip-git-repo-check --sandbox read-only 'Reply with exactly: CODEX_AUTH_OK'
```

A passing `codex exec` proves personal ChatGPT login works, but OpenClaw may still need plugin/harness registration or the correct OpenClaw auth-profile binding.

## Safe investigation sequence

1. Back up config before edits:
   ```bash
   cp <home>/.openclaw/openclaw.json <home>/.openclaw/openclaw.json.pre-codex-runtime-fix.$(date +%Y%m%d-%H%M%S).bak
   ```
2. Inspect model/runtime configuration without printing secrets:
   ```bash
   python3 - <<'PY'
   import json, pathlib
   d=json.loads(pathlib.Path('<home>/.openclaw/openclaw.json').expanduser().read_text())
   defs=d.get('agents',{}).get('defaults',{})
   print('primary=', defs.get('model',{}).get('primary'))
   print('fallbacks=', defs.get('model',{}).get('fallbacks'))
   print('agentRuntime=', defs.get('agentRuntime'))
   print('plugins.codex=', d.get('plugins',{}).get('entries',{}).get('codex'))
   print('auth profile providers=', {k:v.get('provider') for k,v in d.get('auth',{}).get('profiles',{}).items()})
   PY
   ```
3. Check installed docs/package for the Codex harness plugin. In one case, docs referenced `codex` but it was an official external plugin, not bundled in the global npm package.
4. Install/register the official plugin, using force if an earlier install downloaded but failed to persist records:
   ```bash
   openclaw plugins install --force @openclaw/codex
   openclaw plugins registry --refresh
   openclaw plugins list | grep -i -C 5 codex
   ```
5. Ensure config enables plugin id `codex` and restart gateway:
   ```bash
   openclaw gateway restart
   ```
6. Verify boundedly:
   ```bash
   timeout 45 openclaw status
   timeout 45 openclaw gateway probe
   timeout 45 openclaw gateway stability
   ps -o pid,ppid,%cpu,%mem,rss,etime,stat,command -p "$(pgrep -f 'openclaw/dist/index.js gateway --port 18789' | head -1)"
   ```

## Interpreting outcomes

- If `Requested agent harness "codex" is not registered` disappears after plugin install, plugin registration is fixed.
- If the next error is `codex app-server startup aborted`, stop treating it as plugin-not-found; investigate Codex app-server auth/profile/env or temporarily enable fallback to PI for recovery.
- `codex app-server` is expected for the native route: OpenClaw spawns Codex locally (usually `codex app-server --listen stdio://`) as the runtime harness for `agentRuntime.id = "codex"`. It is not needed for the PI OAuth route (`openai-codex/gpt-*`).
- A personal `codex exec` auth smoke test can pass while the native harness still fails, because OpenClaw may start Codex in an isolated per-agent environment and/or pass an OpenClaw `openai-codex` OAuth profile into the app-server.
- If `status` and `gateway probe` pass but CPU remains high and `stability` shows event-loop delay/queued work, call it functional recovery but not full stability. Inspect sessions and queued/stuck work before further config churn.
- After a restart, the gateway can show ~100% CPU and fail a 3s probe for the first minute or two while plugins/sessions settle. Re-check with bounded probes before declaring failure; in the observed recovery CPU dropped from ~103% to ~1%, probe passed, and queue depth became 0 after ~2 minutes.

## Normalizing native Codex model config

If the user wants a clean native Codex configuration with no model fallback churn, normalize only GPT/Codex agents (preserve non-OpenAI agents such as Anthropic reviewers):

- `agents.defaults.model.primary = "openai/gpt-5.5"`
- `agents.defaults.model.fallbacks = []`
- `agents.defaults.agentRuntime = { "id": "codex", "fallback": "none" }`
- `agents.defaults.heartbeat.model = "openai/gpt-5.5"` if it points at an OpenAI/Codex GPT model
- each GPT/Codex agent model -> `openai/gpt-5.5`, fallbacks -> `[]`, runtime -> `{ "id": "codex", "fallback": "none" }`
- keep `openai-codex` auth profiles; those may still be used for OAuth/auth bridging even when the active model route is `openai/gpt-*`.

Create a timestamped backup first. After edits, restart the gateway and verify read-back plus runtime:

```bash
openclaw gateway restart
sleep 90
openclaw gateway probe
openclaw status
openclaw gateway stability
```

Expect existing/stored sessions to still display their historical pinned model (`gpt-5.4`, etc.) until they are reset or superseded; the default and new sessions should show `gpt-5.5`.

## Pitfalls

- Avoid running `openclaw health` unbounded when the gateway is wedged; use `timeout`.
- Do not print `<home>/.openclaw/openclaw.json` or logs raw; redact emails, tokens, API keys, bot tokens, and auth headers.
- Do not conflate `openai-codex/*` with the native subscription route. It is the PI OAuth route, but `openai-codex:*` auth profiles can still be relevant as credentials for native Codex app-server login bridging.
- Do not keep retrying plugin installs blindly after `ConfigMutationConflictError`; check whether the package exists under `<home>/.openclaw/npm/node_modules/@openclaw/codex` and whether the registry/install records know about it.
- User preference from this incident: when a side-effecting system recovery is functionally verified but still noisy (CPU/event-loop warnings), stop and summarize unless asked to keep stabilizing.
