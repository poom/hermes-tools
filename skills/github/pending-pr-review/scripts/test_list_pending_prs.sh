#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cat >"$TMPDIR/gh" <<'GH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"${GH_ARGS_LOG:?}"
cat <<'JSON'
[
  {"number":1,"title":"kept","author":{"login":"alice","type":"User","is_bot":false},"url":"https://example/pr/1","repository":{"name":"repo"},"labels":[],"isDraft":false},
  {"number":2,"title":"draft","author":{"login":"bob","type":"User","is_bot":false},"url":"https://example/pr/2","repository":{"name":"repo"},"labels":[],"isDraft":true},
  {"number":3,"title":"automerge","author":{"login":"carol","type":"User","is_bot":false},"url":"https://example/pr/3","repository":{"name":"repo"},"labels":[{"name":"automerge"}],"isDraft":false},
  {"number":4,"title":"bot","author":{"login":"dependabot","type":"Bot","is_bot":true},"url":"https://example/pr/4","repository":{"name":"repo"},"labels":[],"isDraft":false},
  {"number":5,"title":"finn devops user","author":{"login":"finn-devops","type":"User","is_bot":false},"url":"https://example/pr/5","repository":{"name":"repo"},"labels":[],"isDraft":false},
  {"number":6,"title":"dependabot bracket bot","author":{"login":"dependabot[bot]","type":"User","is_bot":false},"url":"https://example/pr/6","repository":{"name":"repo"},"labels":[],"isDraft":false}
]
JSON
GH
chmod +x "$TMPDIR/gh"

OUT="$(GH_ARGS_LOG="$TMPDIR/gh_args.log" PATH="$TMPDIR:$PATH" "$ROOT/scripts/list_pending_prs.sh" --json --owner test-org --reviewer poom --limit 10)"
OUT_JSON="$OUT" GH_ARGS_LOG="$TMPDIR/gh_args.log" python3 - <<'PY'
import json, os
prs = json.loads(os.environ['OUT_JSON'])
assert [pr['number'] for pr in prs] == [1], prs
assert prs[0]['repository']['name'] == 'repo'
args = open(os.environ['GH_ARGS_LOG']).read()
for qualifier in ['-author:finn-devops', '-author:dependabot[bot]', '-author:dependabot', '-author:codegen-sh']:
    assert qualifier in args, args
assert '--draft=false' in args, args
assert ' -- ' in args, args
PY

TEXT="$(GH_ARGS_LOG="$TMPDIR/gh_args.log" PATH="$TMPDIR:$PATH" "$ROOT/scripts/list_pending_prs.sh" --owner test-org --reviewer poom --limit 10)"
case "$TEXT" in
  *"1 pending PR(s) awaiting review"*"Local filtering dropped 5 raw result(s)"*"[repo #1] kept"*) ;;
  *) printf 'unexpected text output:\n%s\n' "$TEXT" >&2; exit 1 ;;
esac

STATS="$(GH_ARGS_LOG="$TMPDIR/gh_args.log" PATH="$TMPDIR:$PATH" "$ROOT/scripts/list_pending_prs.sh" --stats-json --owner test-org --reviewer poom --limit 6)"
STATS_JSON="$STATS" python3 - <<'PY'
import json, os
payload = json.loads(os.environ['STATS_JSON'])
assert [pr['number'] for pr in payload['prs']] == [1], payload
stats = payload['filter_stats']
assert stats['raw_fetched'] == 6, stats
assert stats['kept_after_local_filter'] == 1, stats
assert stats['dropped_by_local_filter'] == 5, stats
assert stats['hit_limit'] is True, stats
assert stats['risk_hidden_by_local_filter'] is True, stats
assert stats['dropped_breakdown'] == {'automerge': 1, 'bot_author': 1, 'draft': 1, 'excluded_author': 2}, stats
PY
