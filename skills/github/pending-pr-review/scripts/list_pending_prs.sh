#!/usr/bin/env bash
# list_pending_prs.sh — List open PRs pending a user's review in a GitHub org.
# Defaults preserve Poom's OpenClaw workflow.
# Usage:
#   list_pending_prs.sh [--json] [--owner ewa-services] [--reviewer poom] [--limit 300]
#
# Note: GitHub search applies --limit before local filtering. Bot-heavy authors are
# excluded in the GitHub search query itself so they do not consume the raw result
# limit; local filtering remains as a safety net for drafts/bots/automerge.

set -euo pipefail

JSON_MODE=0
STATS_JSON_MODE=0
OWNER="${PENDING_PR_OWNER:-ewa-services}"
REVIEWER="${PENDING_PR_REVIEWER:-poom}"
LIMIT="${PENDING_PR_LIMIT:-300}"
DEFAULT_EXCLUDED_AUTHORS=("finn-devops" "dependabot[bot]" "dependabot" "codegen-sh")
if [[ -n "${PENDING_PR_EXCLUDED_AUTHORS:-}" ]]; then
  IFS=',' read -r -a EXCLUDED_AUTHORS <<<"$PENDING_PR_EXCLUDED_AUTHORS"
else
  EXCLUDED_AUTHORS=("${DEFAULT_EXCLUDED_AUTHORS[@]}")
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      JSON_MODE=1
      shift
      ;;
    --stats-json)
      STATS_JSON_MODE=1
      shift
      ;;
    --owner)
      OWNER="${2:?--owner requires a value}"
      shift 2
      ;;
    --reviewer)
      REVIEWER="${2:?--reviewer requires a value}"
      shift 2
      ;;
    --limit)
      LIMIT="${2:?--limit requires a value}"
      shift 2
      ;;
    -h|--help)
      sed -n '1,12p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required" >&2
  exit 127
fi

EXCLUDE_QUERY=()
for author in "${EXCLUDED_AUTHORS[@]}"; do
  [[ -n "$author" ]] || continue
  EXCLUDE_QUERY+=("-author:${author}")
done
EXCLUDED_AUTHORS_CSV="$(IFS=,; echo "${EXCLUDED_AUTHORS[*]}")"

RAW=$(gh search prs \
  --review-requested="$REVIEWER" \
  --state=open \
  --draft=false \
  --owner="$OWNER" \
  --json number,title,author,url,repository,labels,isDraft \
  --limit "$LIMIT" \
  -- "${EXCLUDE_QUERY[@]}")

FILTERED=$(RAW_JSON="$RAW" EXCLUDED_AUTHORS="$EXCLUDED_AUTHORS_CSV" python3 - <<'PY'
import json, os
prs = json.loads(os.environ['RAW_JSON'])
excluded_authors = {item for item in os.environ.get('EXCLUDED_AUTHORS', '').split(',') if item}
result = []
for pr in prs:
    if pr.get('isDraft'):
        continue
    labels = [l.get('name', '') for l in pr.get('labels') or []]
    if 'automerge' in labels:
        continue
    author = pr.get('author') or {}
    login = author.get('login', '')
    if author.get('is_bot') or author.get('type') == 'Bot':
        continue
    if '[bot]' in login or login in excluded_authors:
        continue
    result.append(pr)
print(json.dumps(result))
PY
)

STATS=$(RAW_JSON="$RAW" FILTERED_JSON="$FILTERED" EXCLUDED_AUTHORS="$EXCLUDED_AUTHORS_CSV" LIMIT="$LIMIT" python3 - <<'PY'
import json, os
raw = json.loads(os.environ['RAW_JSON'])
filtered = json.loads(os.environ['FILTERED_JSON'])
excluded_authors = {item for item in os.environ.get('EXCLUDED_AUTHORS', '').split(',') if item}
breakdown = {}
dropped = []
for pr in raw:
    labels = [l.get('name', '') for l in pr.get('labels') or []]
    author = pr.get('author') or {}
    login = author.get('login', '')
    reason = None
    if pr.get('isDraft'):
        reason = 'draft'
    elif 'automerge' in labels:
        reason = 'automerge'
    elif author.get('is_bot') or author.get('type') == 'Bot':
        reason = 'bot_author'
    elif '[bot]' in login or login in excluded_authors:
        reason = 'excluded_author'
    if reason:
        breakdown[reason] = breakdown.get(reason, 0) + 1
        dropped.append({
            'reason': reason,
            'repository': (pr.get('repository') or {}).get('name', ''),
            'number': pr.get('number'),
            'author': login,
            'title': pr.get('title', ''),
            'url': pr.get('url', ''),
        })
limit = int(os.environ.get('LIMIT') or 0)
raw_count = len(raw)
dropped_count = len(dropped)
print(json.dumps({
    'limit': limit,
    'raw_fetched': raw_count,
    'kept_after_local_filter': len(filtered),
    'dropped_by_local_filter': dropped_count,
    'hit_limit': bool(limit and raw_count >= limit),
    'risk_hidden_by_local_filter': bool(limit and raw_count >= limit and dropped_count > 0),
    'dropped_breakdown': breakdown,
    'dropped': dropped,
}, sort_keys=True))
PY
)

if [[ "$STATS_JSON_MODE" -eq 1 ]]; then
  STATS_JSON="$STATS" FILTERED_JSON="$FILTERED" python3 - <<'PY'
import json, os
print(json.dumps({
    'filter_stats': json.loads(os.environ['STATS_JSON']),
    'prs': json.loads(os.environ['FILTERED_JSON']),
}, indent=2, sort_keys=True))
PY
elif [[ "$JSON_MODE" -eq 1 ]]; then
  printf '%s\n' "$FILTERED"
else
  FILTERED_JSON="$FILTERED" STATS_JSON="$STATS" python3 - <<'PY'
import json, os
prs = json.loads(os.environ['FILTERED_JSON'])
stats = json.loads(os.environ['STATS_JSON'])
print(f'{len(prs)} pending PR(s) awaiting review:')
print(f"Local filtering dropped {stats['dropped_by_local_filter']} raw result(s) after GitHub search limit {stats['limit']}.")
if stats.get('risk_hidden_by_local_filter'):
    print('WARNING: raw results hit the limit and local filtering dropped items; valid PRs may be hidden beyond the limit.')
print()
for pr in prs:
    repo = pr['repository']['name']
    num = pr['number']
    title = pr['title'][:80]
    author = pr['author']['login']
    url = pr['url']
    print(f'  [{repo} #{num}] {title}')
    print(f'    Author: {author} | {url}')
    print()
PY
fi
