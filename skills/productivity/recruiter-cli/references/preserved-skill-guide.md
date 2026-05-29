# Preserved Recruiter CLI Guide

This reference preserves the previous detailed operating guide. Use it for step-by-step procedures after the lean `SKILL.md` routes to this skill.

## Previous Frontmatter

```yaml
name: recruiter-cli
description: "Use when the user asks to use the FINN recruiter CLI or Greenhouse via `recruiter`: run normal subcommands when available, fall back to `recruiter api` for missing/better queries, and review resumes by turning CLI prompts into subagent-reviewed summaries."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [recruiter-cli, greenhouse, recruiting, resume-review, interviews, candidates]
    related_skills: [greenhouse-recruiting]
```

## Previous Operating Guide

# Recruiter CLI

## Overview

Use the local `recruiter` command for FINN recruiting workflows. The binary is `recruiter`, not `recruit`. It wraps Greenhouse Harvest API and also provides higher-level subcommands for jobs, candidates, resume extraction, review prompt generation, scorecards, stage moves, and pipeline summaries.

Default strategy:

1. If the user's request maps to a normal `recruiter` subcommand, use that first.
2. If there is no subcommand, the subcommand output is missing needed fields, or direct API is clearly better, use `recruiter api`.
3. Mix both when useful: e.g. use a subcommand to find IDs, then `recruiter api` to inspect scorecards, activity feed, scheduled interviews, or custom fields.
4. For resume review, prefer prompt-first: run `recruiter review <application_id>` or `recruiter prepare-reviews ...`, then have Hermes/subagents analyze the generated prompt. Do not default to `--ai` unless the user explicitly asks the CLI itself to run AI.
5. For resume-review threads, once candidate name and role/position are known, rename the thread to `<Position - Candidate name>` when the platform/tooling supports thread renaming. If renaming is unavailable in the current environment, include the suggested thread title in the final answer.

Keep Discord responses easy to read: avoid dense tables; use short bullets or numbered lists.

## When to Use

Use this skill when the user asks things like:

- "use recruiter CLI"
- "review resume - application id 67713657101"
- "review resume Harjeet Singh"
- "find my interviews in the next 7 days"
- "show pending reviews"
- "summarize pipeline for job X"
- "who interviewed candidate X?"
- "advance / reject / move this candidate" (confirm before write actions)
- "use recruit/recruiter api"

Do not use this for generic GitHub, Linear, or non-recruiting tasks.

## Core Commands

```bash
recruiter --help
recruiter config --show
recruiter jobs --mine --json
recruiter candidates <job_id> --status active --json
recruiter candidate <candidate_id> --json
recruiter stages <job_id>
recruiter pending-reviews --mine --json
recruiter resume <application_id>
recruiter review <application_id>
recruiter prepare-reviews <job_id>
recruiter summary <job_id>
recruiter scorecard <candidate_review_file>
```

Continuation:

```bash
recruiter api /scheduled_interviews -q per_page=100
```

ID meanings:

- `job_id`: Greenhouse job ID
- `application_id`: one candidate's application to one job; used by `review`, `resume`, `advance`, `move`, `reject`
- `candidate_id`: person record across applications; used by `candidate` and candidate activity feed

## Command Selection Rules

### Prefer normal subcommands for these requests

- List jobs: `recruiter jobs --mine --json`
- Job details: `recruiter job <job_id> --json`
- Job stages: `recruiter stages <job_id>`
- List candidates for a job: `recruiter candidates <job_id> --status active --json`
- Candidate profile: `recruiter candidate <candidate_id> --json`
- Pending resume reviews: `recruiter pending-reviews --mine --json` or `recruiter pending-reviews <job_id> --json`
- Extract resume: `recruiter resume <application_id>`
- Generate resume-review prompt: `recruiter review <application_id>`
- Prepare many review prompts: `recruiter prepare-reviews <job_id>` or `recruiter prepare-reviews --mine`
- Pipeline prompt: `recruiter summary <job_id>`
- Scorecard from a saved review file: `recruiter scorecard <file>`

### Use `recruiter api` for these requests

- Scheduled interviews across all jobs: `/scheduled_interviews`
- Interview details for one application: `/applications/<application_id>/scheduled_interviews`
- Scorecards: `/applications/<application_id>/scorecards`
- Application details: `/applications/<application_id>`
- Candidate activity feed: `/candidates/<candidate_id>/activity_feed`
- Candidate notes/emails: `/candidates/<candidate_id>/activity_feed/notes` or `/emails`
- Ordered job stage metadata: `/jobs/<job_id>/stages`
- Write a custom field or activity note only when explicitly requested/confirmed.

Examples:

```bash
recruiter api /applications/67713657101
recruiter api /applications/67713657101/scheduled_interviews
recruiter api /applications/67713657101/scorecards
recruiter api /candidates/<candidate_id>/activity_feed
recruiter api /scheduled_interviews -q starts_after=2026-05-09T00:00:00Z -q ends_before=2026-05-16T00:00:00Z -q per_page=100
```

## Resume Review Workflow

### Case A: User gives application ID

Example user request:

> review resume - application id 67713657101

Steps:

1. Generate the review prompt, not AI output:
   ```bash
   recruiter review 67713657101
   ```
2. If needed, fetch metadata:
   ```bash
   recruiter api /applications/67713657101
   recruiter api /applications/67713657101/scorecards
   recruiter api /applications/67713657101/scheduled_interviews
   ```
3. Send the prompt content to a `delegate_task` subagent for evaluation. The subagent should return the review text; it should not write files or post to Greenhouse.
4. Final answer to the user should be a readable resume review with:
   - Candidate / role / application ID
   - Fit score 1-5
   - Confidence
   - Recommendation: advance / hold / reject
   - Short decision reason
   - Evidence bullets
   - Gaps/risks
   - Follow-up questions
5. Do not post scorecards, advance, move, or reject unless the user explicitly asks. For irreversible or external write actions, confirm scope first.

Subagent instruction template:

```text
You are reviewing a FINN candidate using the recruiter CLI prompt below.
Score only the exact applied role unless the prompt explicitly asks for alternate roles.
Return concise markdown/plain text, not JSON, with:
- Candidate / role / application ID
- Fit Score 1-5
- Confidence
- Recommendation: advance / hold / reject
- Decision Reason
- Evidence
- Gaps / Risks
- Follow-up Questions
Do not invent facts outside the prompt.
```

Continuation:

```text

<PROMPT>
...
</PROMPT>
```

If the prompt is small enough and no parallel work is needed, Hermes may review it directly. For long resumes or multiple candidates, use subagents.

### Case B: User gives a candidate name

Example user request:

> Review resume Harjeet Singh

Steps:

1. Search pending review queues first:
   ```bash
   recruiter pending-reviews --mine --json
   ```
   Filter locally by case-insensitive candidate name.
2. If no match or ambiguous, list jobs and scan active candidates:
   ```bash
   recruiter jobs --mine --json
   recruiter candidates <job_id> --status active --json
   ```
3. If still no match, use direct API pagination and local filtering. Do not trust `recruiter api /candidates -q query=<name>` unless you verify the returned names actually match; in this setup it may return an unfiltered first page.
4. If exactly one matching application is found, run the application-ID workflow above.
5. If multiple matches exist, answer with a short disambiguation list: name, role, stage, application ID. Ask the user which one to review.

Name-search Python pattern using the CLI:

```python
import json, subprocess
name = "harjeet singh".lower()

# Start with pending reviews.
p = subprocess.run(["recruiter", "pending-reviews", "--mine", "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
items = json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else []

matches = []
for item in items:
    text = json.dumps(item).lower()
    if all(part in text for part in name.split()):
        matches.append(item)
```

Continuation:

```python
print(json.dumps(matches, indent=2))
```

If `pending-reviews` output shape is not enough, scan `jobs --mine --json` then `candidates <job_id> --json` and filter the same way.

### Case C: User asks to review a batch

Use the repo skill pattern:

1. `recruiter prepare-reviews <job_id>` or `recruiter prepare-reviews --mine`
2. Read `<home>/.config/recruiter/output/<job-slug>/manifest.json`
3. Split candidates into small batches.
4. Send prompt file contents to subagents.
5. Main thread writes returned review files if the user wants files saved.
6. Summarize the queue for the user.
7. Only post scorecards with `recruiter scorecard <file> --post` if explicitly requested.

## Interview Lookup Workflow

For "my interviews in the next N days":

1. Get current time with `date` or Python; do not guess.
2. Read the Greenhouse user ID from `recruiter config --show` only for a masked check, or from recruiter config in Python if necessary.
3. Query:
   ```bash
   recruiter api /scheduled_interviews \
     -q starts_after=<now_utc> \
     -q ends_before=<end_utc> \
     -q per_page=100
   ```
4. Filter locally where `interviewers[].id` equals the configured user ID, or `organizer.id` equals the user ID.
5. For each match, fetch `/applications/<application_id>` and `/candidates/<candidate_id>` to get candidate and job names.
6. Convert UTC times to the user's local timezone when clear from context; otherwise label UTC.

Keep output simple in Discord:

```text
Found 5 interviews in the next 7 days.

1. Tue May 12, 12:00-14:00 +07
Candidate Name
Role
Interview type
```

## Candidate Status Workflow

For "what is happening with candidate X" or "who interviewed them":

1. Resolve candidate/application IDs.
2. Fetch application:
   ```bash
   recruiter api /applications/<application_id>
   ```
3. Fetch interviews:
   ```bash
   recruiter api /applications/<application_id>/scheduled_interviews
   ```
4. Fetch scorecards:
   ```bash
   recruiter api /applications/<application_id>/scorecards
   ```
5. Fetch activity feed if next steps are unclear:
   ```bash
   recruiter api /candidates/<candidate_id>/activity_feed
   ```
6. Fetch job stages if you need to infer next stage:
   ```bash
   recruiter api /jobs/<job_id>/stages
   ```
7. Answer with status, current stage, interviewers, scorecard recommendations, and next step. Avoid exposing emails, phone numbers, signed attachment URLs, or long email bodies unless explicitly requested.

## Write Actions and Safety

These commands change Greenhouse state:

```bash
recruiter scorecard <file> --post
recruiter advance <application_id> -y --note "..."
recruiter move <application_id> --to <stage_id> -y --note "..."
recruiter reject <application_id> -y --note "..."
recruiter api <endpoint> -X POST|PATCH|PUT|DELETE ...
```

Before write actions:

- Confirm exactly which candidate/application ID and action.
- Summarize the note/body that will be posted.
- Use dry-run/read-only command first if available, e.g. `recruiter scorecard <file>` before `--post`.
- After posting/moving/rejecting, verify by fetching the application or activity feed.

## Output Style for Discord

Prefer this shape:

```text
I found one match:
Harjeet Singh
Application: 67713657101
Role: Backend Engineer
Stage: Resume Review

Review:
Fit: 4/5
Confidence: Medium
Recommendation: advance

Why:
```

Continuation:

```text
- ...

Risks:
- ...

Follow-up questions:
1. ...
2. ...
```

Avoid large markdown tables in Discord unless the user asks for a file/report.

## Common Pitfalls

1. The command is `recruiter`, not `recruit`.
2. `recruiter api /candidates -q query=<name>` may not truly search by name. Verify returned names or use local filtering over pending reviews / job candidates / paginated API results.
3. Do not count a scheduled-interview attendee with null Greenhouse user ID as an interviewer; it may be the candidate.
4. Do not use `--ai` by default for resume review. The preferred workflow is prompt-first, then Hermes/subagents review the prompt.
5. Do not post scorecards or advance/reject candidates without explicit user approval.
6. Avoid leaking PII: emails, phone numbers, resume attachment URLs, and full email bodies should stay out of chat unless specifically needed.
7. If a CLI subcommand times out or lacks fields, use `recruiter api` endpoints directly and filter locally.

## Verification Checklist

- [ ] Used `recruiter` CLI or `recruiter api`, not guessed data.
- [ ] Resolved ID type correctly: job vs application vs candidate.
- [ ] For resume review, generated prompt with `recruiter review <application_id>` or prepared prompt files.
- [ ] Used subagent/direct review on the prompt and did not invent facts.
- [ ] For name-only requests, disambiguated multiple matches before reviewing.
- [ ] For write actions, got explicit approval and verified the result.
- [ ] Final Discord answer is readable without dense tables.
