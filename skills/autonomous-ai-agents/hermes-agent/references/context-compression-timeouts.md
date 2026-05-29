# Context compression timeout troubleshooting

Session-derived notes for Hermes context compaction/compression failures, especially in gateway sessions during long PR reviews.

## Symptoms

Manual `/compress` or automatic context compression may fail with a timeout message like:

```text
Codex auxiliary Responses stream exceeded 120.0s total timeout
```

This can happen when the auxiliary compression model is routed through OpenAI Codex Responses and the summary generation takes longer than the configured auxiliary timeout.

A separate failure mode is a Codex/OpenAI client connection error, often surfaced to the user as:

```text
⚠️ Summary generation failed (Connection error.). 2 historical message(s) were removed and replaced with a placeholder; earlier context is no longer recoverable. Consider checking your auxiliary.compression model configuration.
```

The corresponding logs can show:

```text
Auxiliary compression: using auto (gpt-5.5) at https://chatgpt.com/backend-api/codex/
Auxiliary compression: connection error on auto (Connection error.), trying fallback
Auxiliary compression: connection error on auto and no fallback available (tried: openrouter, nous, local/custom, api-key)
Failed to generate context summary: Connection error.. Further summary attempts paused for 60 seconds.
RuntimeError: Cannot send a request, as the client has been closed.
openai.APIConnectionError: Connection error.
```

Interpretation: this is not a timeout. The underlying HTTP client was already closed before the auxiliary compression request could be sent.

## Configuration path

Compression summary generation uses the auxiliary task timeout:

```yaml
auxiliary:
  compression:
    timeout: 120  # default in many configs
```

The runtime path is:

- `gateway/run.py::_handle_compress_command` handles `/compress`.
- `agent/context_compressor.py` invokes compression.
- `agent/auxiliary_client.py::call_llm(task="compression", ...)` reads `auxiliary.compression.timeout` via `_get_task_timeout()`.
- `_CodexCompletionsAdapter` forwards that timeout to `client.responses.stream(timeout=...)` and also enforces a total wall-clock timeout while consuming streaming events.

## Practical fix

For users who run long reviews or large gateway threads, raise the compression timeout:

```bash
hermes config set auxiliary.compression.timeout 600
```

Then restart the gateway or start a new CLI session if the running process needs to pick up config changes:

```bash
hermes gateway restart
```

## Connection-error log triage

When the user asks what the connection error was, show exact evidence rather than summarizing vaguely.

1. Search recent logs for compression/session-search/title auxiliary failures:
   ```bash
   python - <<'PY'
   from pathlib import Path
   import os, re
   logdir = Path(os.path.expanduser('<home>/.hermes/logs'))
   terms = re.compile(r'connection error|ConnectionError|client has been closed|failed to generate context summary|Manual compress failed|openai.APIConnectionError', re.I)
   for path in sorted(logdir.glob('*.log')):
       try:
           lines = path.read_text(errors='replace').splitlines()[-2000:]
       except Exception:
           continue
       hits = [ln for ln in lines if terms.search(ln)]
       if hits:
           print(f'--- {path} ---')
           for ln in hits[-30:]:
               print(ln)
   PY
   ```
2. If traceback context is needed, read a range around the latest `openai.APIConnectionError: Connection error.` in `errors.log` or `gateway.error.log`.
3. To confirm what `/compress` wrote, inspect the continuation transcript named in the log line `Session split detected: <old> → <new> (compression)`:
   ```bash
   sed -n '1,12p' <home>/.hermes/sessions/<new_session_id>.jsonl
   ```
   Fallback compression writes a `[CONTEXT COMPACTION — REFERENCE ONLY]` placeholder with text such as `Summary generation was unavailable`.
4. In the final answer, include three pieces only unless asked for more: the relevant auxiliary log lines, the underlying exception, and the user-facing compression warning/placeholder consequence.

## Verification commands

From the Hermes source checkout:

```bash
python - <<'PY'
from agent.auxiliary_client import _get_task_timeout
print(_get_task_timeout('compression'))
PY
```

Focused tests:

```bash
python -m pytest tests/gateway/test_compress_command.py tests/agent/test_context_compressor.py -q -o 'addopts='
python -m pytest tests/agent/test_auxiliary_client.py::TestCodexAuxiliaryAdapterTimeout tests/hermes_cli/test_aux_config.py -q -o 'addopts='
```

A cheap adapter-forwarding smoke test:

```bash
python - <<'PY'
from types import SimpleNamespace
from agent.auxiliary_client import _get_task_timeout, _CodexCompletionsAdapter

class FakeStream:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False
    def __iter__(self): return iter(())
    def get_final_response(self):
        return SimpleNamespace(output=[SimpleNamespace(type='message', content=[SimpleNamespace(type='output_text', text='ok')])], usage=None)
class FakeResponses:
    def __init__(self): self.kwargs = None
```

Continuation:

```bash
    def stream(self, **kwargs): self.kwargs = kwargs; return FakeStream()

fake = SimpleNamespace(responses=FakeResponses())
adapter = _CodexCompletionsAdapter(fake, 'gpt-5.5')
timeout = _get_task_timeout('compression')
resp = adapter.create(messages=[{'role':'user','content':'summarize'}], timeout=timeout)
print({'compression_timeout': timeout, 'forwarded_timeout': fake.responses.kwargs.get('timeout'), 'content': resp.choices[0].message.content})
PY
```

Expected result after raising timeout: `compression_timeout` and `forwarded_timeout` both show the new value (for example `600.0`).
