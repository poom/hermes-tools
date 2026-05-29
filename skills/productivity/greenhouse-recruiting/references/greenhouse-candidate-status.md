# Candidate Status Lookup via Greenhouse Harvest API

Session-derived pattern for cases where a user asks: “what is candidate X's status; who interviewed them; what is next?”

## Useful endpoints

- Candidate/application record: `/applications/<application_id>`
- Scheduled/completed interviews: `/applications/<application_id>/scheduled_interviews`
- Scorecards/recommendations: `/applications/<application_id>/scorecards`
- Candidate activity feed: `/candidates/<candidate_id>/activity_feed`
- Ordered job stages: `/jobs/<job_id>/stages` (sort by `priority`)

## Search pattern when only a first name is given

The local `recruiter api /candidates -q query=<name>` call may not filter by name. If it returns unrelated names, switch to paginated local filtering. For broad scans:

```python
import base64, time, httpx
from recruiter import config

headers = {
    "Authorization": "Basic " + base64.b64encode((config.get_greenhouse_token() + ":").encode()).decode(),
    "Content-Type": "application/json",
}
client = httpx.Client(base_url="https://harvest.greenhouse.io/v1", headers=headers, timeout=30.0)

def get(path, params):
    for _ in range(10):
        r = client.get(path, params=params)
```

Continuation:

```python
        if r.status_code != 429:
            r.raise_for_status()
            return r
        time.sleep(int(r.headers.get("Retry-After", "5") or 5) + 1)
    r.raise_for_status()

page = 1
matches = []
while True:
    r = get("/candidates", {"updated_after": "2026-01-01T00:00:00Z", "per_page": 500, "page": page})
    for c in r.json():
        name = f"{c.get('first_name','')} {c.get('last_name','')}".strip()
```

Continuation:

```python
        if "harshit" in name.lower():
            matches.append((c["id"], name, c.get("application_ids")))
    if 'rel="next"' not in (r.headers.get("link") or ""):
        break
    page += 1
```

Use narrower `created_after` / `updated_after`, known job IDs, or active-only application scans when possible.

## Interpreting interview facts

- Use scorecards to identify actual interviewers and recommendations:
  - `interviewer.name`
  - `interview` / `interview_step.name`
  - `overall_recommendation`
  - `questions[].answer` for takeaways
- Use scheduled interviews to confirm events and attendees, but ignore attendee rows where `id` and `name` are null and the email belongs to the candidate.
- Use activity feed for next-step communication. Emails/notes often explicitly state “schedule remaining interviews” or “send availability.” Prefer that over inferring from stage order.

## Example outcome shape

- Candidate: `<name>`
- Role: `<job name>`
- Status/current stage: `<active/rejected/etc.>`, `<current_stage.name>`
- Interviewed by:
  - `<stage>`: `<interviewer>` — recommendation `<yes/strong_yes/etc.>`
- Next step:
  - Explicit next step from latest outreach/note, or next job stage by priority if no explicit instruction exists.

## Privacy

Do not include candidate email, phone, signed resume URLs, or full email bodies in the user-facing answer unless explicitly requested. Summarize only the process status and hiring facts.
