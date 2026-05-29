# GitHub search limit-before-filtering pitfall

Observed in a pending-review run for `EWA-Services/Infrastructure#4370`.

## Symptom

A PR can be genuinely review-requested for `poom` and visible via a targeted query, but absent from the pending-review script output.

Example verification pattern:

```bash
gh search prs --review-requested=poom --state=open --owner=ewa-services \
  --json number,title,url,repository,author,labels,isDraft --limit 200 \
  --jq '.[] | select(.repository.nameWithOwner=="EWA-Services/Infrastructure" and .number==4370)'
```

## Cause

`gh search prs --limit N` applies `N` to raw GitHub search results before the pending-review script filters drafts, bot-authored PRs, and `automerge` labels. If many raw bot/automerge/draft results precede a human PR, a low limit can cut it off before filtering.

In the observed case:

- `--limit 100`: PR not present in raw results; filtered output missed it.
- `--limit 150`: still not present.
- `--limit 200`: PR appeared at raw position 160 and survived filtering.

## Durable fix

Keep the script default raw limit high enough for the queue shape, currently `300`, or explicitly pass a larger `--limit` when debugging omissions.

After changing the default, verify with:

```bash
bash <home>/.hermes/skills/github/pending-pr-review/scripts/list_pending_prs.sh --json > /tmp/pending-prs.json
python3 - <<'PY'
import json
prs=json.load(open('/tmp/pending-prs.json'))
print('count', len(prs))
print(any(pr['repository'].get('nameWithOwner')=='EWA-Services/Infrastructure' and pr['number']==4370 for pr in prs))
PY
```

## Review interaction

After a formal current-head review is posted, the GitHub review request for that user is removed. Re-run the pending script to confirm the PR disappeared for the correct reason rather than because of truncation.
