# Resolver Eval

These prompts should trigger `my-open-prs`:

- "Show my open PRs waiting for review."
- "Why did my PRs not merge?"
- "List my ewa-services PRs that need my feedback."
- "Use `is:open is:pr author:@me archived:false org:ewa-services draft:false` and summarize blockers."

These prompts should not trigger `my-open-prs`:

- "Review the code changes in the current branch."
- "Create a new GitHub pull request."
- "Fix failing CI on this checked-out PR."
- "Summarize open Linear issues assigned to me."
