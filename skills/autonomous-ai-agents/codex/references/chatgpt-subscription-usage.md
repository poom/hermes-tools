# ChatGPT Subscription / Codex Usage Checks

Session learning: checking "ChatGPT subscription token usage" from a machine authenticated with Codex CLI is not the same as OpenAI API billing usage.

## What is available

- `codex login status` may show `Logged in using ChatGPT` even when the access token is expired; a real Codex call can still fail with 401.
- Codex CLI stores per-session token accounting in `<home>/.codex/sessions/**/rollout-*.jsonl`.
- Recent Codex session JSONL can include:
  - `payload.info.total_token_usage.{input_tokens,cached_input_tokens,output_tokens,reasoning_output_tokens,total_tokens}`
  - `payload.rate_limits` with `plan_type`, `primary.used_percent`, `secondary.used_percent`, reset timestamps, etc.
- ChatGPT/Codex subscription usage exposes local token logs and rate-limit percentages, not a full official token dashboard equivalent to OpenAI Platform billing.
- OpenAI help pages and chatgpt.com can be Cloudflare/bot-detection blocked from browser automation; prefer CLI/local logs first.

## Quick commands

Check nominal login:

```bash
codex login status
```

If a live call is needed, run in a trusted git repo or pass `--skip-git-repo-check`:

```bash
codex exec --skip-git-repo-check --sandbox read-only --model gpt-5.5 'Return exactly OK'
```

If it fails with `refresh_token_reused` or `token_expired`, tell the user to re-authenticate:

```bash
codex logout
codex login
```

## Local log summarizer

This reads only usage metadata from local Codex JSONL logs, not message bodies:

```bash
python3 - <<'PY'
import json, pathlib, collections, os
root=pathlib.Path.home()/'.codex'/'sessions'
sessions=[]; rate_events=[]
for p in root.rglob('*.jsonl'):
    max_usage=None; first_ts=None; latest_ts=None; model='unknown'
    try:
        for line in p.open(errors='ignore'):
            try: obj=json.loads(line)
            except Exception: continue
            ts=obj.get('timestamp')
            if ts and not first_ts: first_ts=ts
```

Continuation:

```bash
            payload=obj.get('payload') or {}
            if not isinstance(payload, dict): continue
            model=payload.get('model') or model
            info=payload.get('info') or {}
            usage=info.get('total_token_usage') if isinstance(info,dict) else None
            if isinstance(usage,dict) and 'total_tokens' in usage:
                if max_usage is None or (usage.get('total_tokens') or 0) > (max_usage.get('total_tokens') or 0):
                    max_usage=dict(usage); latest_ts=ts
            rl=payload.get('rate_limits')
            if isinstance(rl, dict):
                rate_events.append((ts, str(p), rl))
    except Exception:
```

Continuation:

```bash
        continue
    if max_usage:
        sessions.append({'day': (first_ts or latest_ts or '')[:10], 'model': model, 'usage': max_usage})

for label,prefix in [('current_month','2026-05'),('all_local_logs',None)]:
    agg=collections.Counter(); n=0; by_day=collections.defaultdict(collections.Counter)
    for s in sessions:
        if prefix and not s['day'].startswith(prefix): continue
        n += 1
        for k in ['input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens','total_tokens']:
            agg[k] += int(s['usage'].get(k) or 0)
            by_day[s['day']][k] += int(s['usage'].get(k) or 0)
```

Continuation:

```bash
    print('\n', label, 'sessions_with_usage', n)
    print(dict(agg))
    for d,c in sorted(by_day.items()):
        print(d, dict(c))

print('\nlatest_rate_limit_events')
for ts,p,rl in sorted([x for x in rate_events if x[0]], key=lambda x:x[0])[-5:]:
    print(ts, os.path.basename(p), rl)
PY
```

Adjust the month prefix dynamically for future use, e.g. `date +%Y-%m`.

## Reporting guidance

- Distinguish "local Codex token logs" from "OpenAI API billing usage" and from "current ChatGPT subscription quota".
- If live auth fails, still report local log totals clearly and label stale rate-limit snapshots with timestamps.
- Avoid exposing prompts or session contents; summarize only token/rate-limit metadata.
