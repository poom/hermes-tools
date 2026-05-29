# Resolver Eval

These prompts should trigger `skillify`:

- "Skillify this folder."
- "Validate this skill against the 10 gates."
- "Turn this workflow into a durable skill."
- "Apply the skill promotion checklist to `skills/<target>`."
- "Is this skill robust enough to ship?"
- "Run the skill gate checker on this folder."

These prompts should not trigger it:

- "Install a curated skill." (package manager / plugin tool, not a skill audit)
- "Review this PR." (code review, not skill validation)
- "Summarize this report output." (consumer of a report, not a skill auditor)
- "Score this candidate's resume." (domain skill, unrelated to skill creation)
- "Write a new skill from scratch." (skill *creation* scaffolding lives in a separate `skill-creator` skill; `skillify` audits an existing folder)
