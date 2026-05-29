PR Review Request

- PR: <url or org/repo#number>
- Repo: <owner/repo>
- Worktree: <workspace>/repo/<repo-name>-<pr-number>
- Ticket/Experiment: <links>
- PR type: <feature/bugfix/integration/removal/terraform>
- Result route: <origin Discord thread | origin Telegram topic | explicit target>

Reviewer lanes:
1. Reviewer A: OpenAI Codex / GPT-5.5
2. Reviewer B: direct Claude CLI (`claude -p --model opus ...`), no ACP

Must check:
1. Fresh current head SHA, live diff, changed files, checks, review state
2. Clean code + SOLID
3. Feature-flag safety
   - ON path works
   - OFF path preserves current logic
4. Experiment outcome policy
   - rollout / force-rule / won => integrate kept path
   - lost => force OFF + remove losing variant
5. Terraform/infra plan safety when applicable
   - review plan output
   - block unexplained unrelated destroys/replacements/removals
6. Tests and coverage >= 80% or repo stricter gate
7. Linked ticket / Linear acceptance criteria

Output:
- repo + PR number + title + URL
- verdict
- models used
- blockers
- high-priority issues
- suggested improvements
- feature-flag validation
- experiment-policy validation
- Terraform/plan validation when applicable
- test/coverage result
- merge readiness
- GitHub action taken or not posted
