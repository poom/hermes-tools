# Max-iterations env drift debug trace

## Symptom

Discord long-running status in channel `1506953946894434304` showed:

```text
Still working... (6 min elapsed — iteration 21/60, receiving stream response)
```

The user expected `300` because `<home>/.hermes/config.yaml` had:

```yaml
agent:
  max_turns: 300

delegation:
  max_iterations: 300
```

## Evidence gathered

- `hermes gateway status` showed the active launchd gateway process.
- Startup log for the current gateway contained:

```text
Agent budget: max_iterations=300 (agent.max_turns from config.yaml, or HERMES_MAX_ITERATIONS from .env, or default 90)
```

- `<home>/.hermes/.env` still contained:

```text
HERMES_MAX_ITERATIONS=60
```

- `gateway/run.py` status message path:
  - periodic long-running task builds `Still working...` text.
  - it calls `agent.get_activity_summary()`.
  - `get_activity_summary()` returns `api_call_count` and `max_iterations` from the live `AIAgent` instance.

- `gateway/run.py` per-turn construction path read:

```python
max_iterations = int(os.getenv("HERMES_MAX_ITERATIONS", "90"))
```

before calling the runtime env/config refresh that reasserts `agent.max_turns` over stale env, then passed that early value into `AIAgent(..., max_iterations=max_iterations, ...)`.

## Root cause class

The displayed denominator was not a rendering bug. The live turn's `AIAgent.max_iterations` was actually `60` because a stale `.env` value was read before config authority was restored for that turn.

This can coexist with a correct startup budget log if startup config bridging is correct but a later per-turn path reads env too early.

## Workaround

1. Remove or update `HERMES_MAX_ITERATIONS=60` in `<home>/.hermes/.env`.
2. Restart the gateway.
3. Verify the next live turn uses the intended cap.

## Proper code fix

Move `_reload_runtime_env_preserving_config_authority()` before the per-turn budget read, or recompute `max_iterations` immediately after the refresh and before `AIAgent` construction.

Add/adjust tests so config wins over `.env` both:

- at gateway startup, and
- during per-turn cached/fresh agent creation.

## Source locations to inspect

- `gateway/run.py`: long-running notification task; search for `Still working...`.
- `gateway/run.py`: per-turn `run_sync()`; search for `HERMES_MAX_ITERATIONS` and `AIAgent(`.
- `run_agent.py`: `AIAgent.get_activity_summary()`.
