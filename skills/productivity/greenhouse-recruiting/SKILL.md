---
name: greenhouse-recruiting
description: "Greenhouse recruiting workflows via recruiter CLI and Harvest API: find candidates, inspect applications, interviews, scorecards, and next steps."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [greenhouse, recruiting, recruiter-cli, candidates, interviews, hiring]
---

# Greenhouse Recruiting

Use this skill when the user asks about candidates, interview status, hiring stages, scorecards, next steps, recruiter workflows, or the `recruiter` / Greenhouse CLI.

## Key Commands

- CLI binary is `recruiter` (not `recruit`). Start with:
  ```bash
  recruiter --help
  recruiter candidate <candidate_id> --json
  recruiter candidates <job_id> --status active --json
  recruiter api /applications/<application_id>
  recruiter api /applications/<application_id>/scheduled_interviews
  recruiter api /applications/<application_id>/scorecards
  recruiter api /candidates/<candidate_id>/activity_feed
  recruiter api /jobs/<job_id>/stages
  ```
- The source checkout is usually `$RECRUITER_REPO` or `$HOME/Projects/recruiter`; if the CLI is missing features, inspect `src/recruiter/greenhouse.py` and use its configured token with small Python scripts.

## Candidate Status Workflow

1. **Clarify only if necessary.** If the user gives only a first name, search broadly but call out ambiguity and list likely matches.
2. **Find candidate/application IDs.** Prefer targeted job pipelines if the role is known. If not, search recent candidates/applications with pagination and local name filtering.
3. **Inspect the application.** Fetch `/applications/<application_id>` for current status, current stage, job, recruiter/coordinator, applied date, rejection reason, and custom fields.
4. **Inspect interviews.** Fetch `/applications/<application_id>/scheduled_interviews` for scheduled/completed interview events and interviewers.
5. **Inspect scorecards.** Fetch `/applications/<application_id>/scorecards` for who interviewed, submitted recommendations, and takeaways. Treat submitted scorecards as stronger evidence than scheduled interview attendee lists.
6. **Inspect activity feed.** Fetch `/candidates/<candidate_id>/activity_feed` for stage moves, outreach emails, notes, availability, and explicit next-step communication.
7. **Inspect job stages.** Fetch `/jobs/<job_id>/stages`, sort by `priority`, and infer the next stage after the current one only when there is no explicit next-step email/note.
8. **Answer concisely.** Include candidate name, role, status/current stage, who interviewed them, scorecard recommendations if present, and the next step. Avoid exposing personal contact details unless the user explicitly needs them.

## Pitfalls

- `recruiter api /candidates -q query=Name` does **not** perform name search in this setup; it can return the first page unfiltered. Verify search behavior by checking returned names.
- Large Greenhouse scans can time out or hit 429 rate limits. Use `per_page=500`, paginate deliberately, and back off on `Retry-After`. Avoid high-concurrency scans.
- There may be many partial name matches. For “Harshit,” likely matches included several active/rejected candidates; use role, current stage, recent interview activity, or user follow-up to disambiguate.
- Scheduled interviews may include the candidate as an attendee with a null Greenhouse user ID. Do not count that as an interviewer.
- Activity feed output can be large and contain PII/email bodies. Extract only hiring-process facts needed for the answer.

## References

- `references/greenhouse-candidate-status.md` — reusable API probing pattern and example interpretation from the Harshit candidate-status lookup.
