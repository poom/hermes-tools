# Static HTML org chart / roster-sync PR reviews

Use this when a PR updates a static org chart, employee roster, department filters, or similar data embedded in a single HTML/JS file.

## Review pattern

1. Treat the roster as data with UI contracts, not just a text diff.
2. Validate the source-of-truth/ticket context separately from the PR description when available (for example Linear ticket and author comments about People-team decisions).
3. Check prior review threads first; stale filter/department comments are common after rebases/data refreshes.
4. Run local static data validation:
   - parse the embedded `orgData`/data array;
   - verify one intended root;
   - verify unique IDs and unique emails where applicable;
   - verify every `pid`/parent reference resolves;
   - verify no cycles if the tree can be traversed;
   - verify every filter button value exactly matches at least one data department/category;
   - verify every non-hidden/non-root department/category has a matching filter button;
   - verify displayed counts exclude virtual/open placeholder rows and include intentionally rendered advisory/badge rows only when documented.
5. Browser-smoke the static page when practical:
   - load `file:///.../index.html` or the PR preview;
   - check for console errors;
   - read the visible header/count;
   - click or programmatically invoke each filter and confirm chart data/render count is non-empty and plausible.
6. If external People/HR spreadsheet data is not accessible, be explicit: approve only the code/data-contract consistency, and rely on PR comments/ticket evidence for spreadsheet correctness.

## Lightweight validation snippets

When Node/browser evaluation is slow or brittle, a line-oriented parser can still catch most roster regressions for one-line object entries:

```bash
python3 - <<'PY'
import re, pathlib, json
p=pathlib.Path('org-chart.finn-app.com/index.html')
text=p.read_text()
entries=[]
for m in re.finditer(r'^\s*\{ id: "(?P<id>[^"]+)"(?P<body>.*)\},\s*$', text, re.M):
    body=m.group('body')
    def val(k):
        mm=re.search(r'\b'+re.escape(k)+r': "([^"]*)"', body)
        return mm.group(1) if mm else None
    entries.append({k: (m.group('id') if k=='id' else val(k)) for k in ['id','pid','name','role','dept','email','level']})
ids=[e['id'] for e in entries]
emails=[e['email'] for e in entries if e['email']]
errors=[]
if len(ids)!=len(set(ids)): errors.append('duplicate ids')
if len(emails)!=len(set(emails)): errors.append('duplicate emails')
for e in entries:
    if e['pid'] and e['pid'] not in ids:
        errors.append(f"missing parent {e['pid']} for {e['id']}")
roots=[e['id'] for e in entries if not e['pid']]
buttons=[x for x in re.findall(r"filterDept\('([^']+)'\)", text) if x!='all']
depts=sorted(set(e['dept'] for e in entries))
for b in buttons:
    if b not in depts: errors.append(f'button dept missing from data: {b}')
for d in depts:
    if d!='Executive' and d not in buttons: errors.append(f'dept lacks button: {d}')
print(json.dumps({'roots':roots,'nodes':len(entries),'emails':len(set(emails)),'peopleCount':len(set(emails))+1,'depts':depts,'buttons':buttons,'errors':errors}, indent=2))
if errors: raise SystemExit(1)
PY
```

For browser validation, after loading the page use console evaluation like:

```js
({
  title: document.title,
  meta: document.querySelector('.meta')?.innerText,
  buttons: [...document.querySelectorAll('.controls button')].map(b => b.innerText),
  bodyText: document.body.innerText.slice(0, 300),
})
```

If the chart library exposes state (for `d3-org-chart`, `chart.getChartState().allNodes` worked), loop each filter and record counts:

```js
(() => {
  const results = {};
  for (const dept of ['Engineering','Product','Data','Data Science / Credit Risk','Growth / Marketing','Market Expansion','Finance','People','Philippines Operations','Thailand Operations']) {
    event = {target:{classList:{add(){}}}};
    filterDept(dept);
    results[dept] = chart.getChartState().allNodes.length;
  }
  return results;
})()
```

## Process-gate note

For these static roster PRs, old AI/bot `CHANGES_REQUESTED` reviews may continue to hold Policy Bot even after all inline threads are resolved and current-head CI passes. Separate the code verdict from merge readiness:

- Code verdict: approve if the current data/UI contract is correct.
- Merge readiness: call out stale policy/review state as a process blocker requiring dismissal, re-review, or policy-bot re-evaluation.
