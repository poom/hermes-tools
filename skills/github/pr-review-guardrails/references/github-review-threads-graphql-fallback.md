# GitHub review threads GraphQL fallback

Use this when guardrail review requires inline review-thread evidence but the installed `gh` does not support `gh pr view --json reviewThreads`.

## Symptom

```text
Unknown JSON field: "reviewThreads"
```

Do **not** treat this as permission to skip inline threads. Use GitHub GraphQL.

## Minimal probe

```bash
OWNER=EWA-Services
REPO=Tools
PR=147

gh api graphql \
  -f owner="$OWNER" \
  -f repo="$REPO" \
  -F number="$PR" \
  -f query='query($owner:String!,$repo:String!,$number:Int!){
    repository(owner:$owner,name:$repo){
      pullRequest(number:$number){
        reviewThreads(first:100){
```

Continuation:

```bash
          nodes{
            isResolved
            comments(first:20){
              nodes{
                author{login}
                body
                path
                line
                originalLine
                createdAt
                outdated
              }
```

Continuation:

```bash
            }
          }
        }
      }
    }
  }' > /tmp/pr-reviewthreads.json

python3 - <<'PY'
import json
p='/tmp/pr-reviewthreads.json'
data=json.load(open(p))
threads=data['data']['repository']['pullRequest']['reviewThreads']['nodes']
```

Continuation:

```bash
print('threads', len(threads), 'unresolved', sum(not t['isResolved'] for t in threads))
for i,t in enumerate(threads, 1):
    if not t['isResolved']:
        first=(t['comments']['nodes'] or [{}])[0]
        print(i, first.get('path'), first.get('line') or first.get('originalLine'), first.get('author',{}).get('login'))
PY
```

## Evidence to record

- Total thread count and unresolved count.
- Any unresolved blocker thread path/line, latest author reply, and current-code decision.
- If all threads are resolved, record `review threads: <N> total, 0 unresolved` in the review note and synthesis.

## Pitfalls

- The `reviewThreads(first:100)` page is enough for most PRs but not guaranteed. If `pageInfo.hasNextPage` is true, paginate before concluding there are zero unresolved threads.
- GraphQL thread `line` may be null for outdated comments; keep `originalLine` and `outdated` in the evidence so stale findings can be classified correctly.
- Do not paste full thread bodies into chat unless needed; summarize blocker substance and author replies.
