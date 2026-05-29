# Agent Docs Behavioral Eval Framework

## Philosophy

The eval measures whether AGENTS docs help a coding agent do a real task correctly. We use shipped PRs as ground truth but score against the **ticket first, PR second**.

## Process

### 1. Task Selection
Pick shipped PRs from target repos. Prefer small fixes (under 200 lines changed) with clear Linear tickets. The task prompt includes the full Linear ticket description — the agent should follow the ticket, not reverse-engineer the PR.

### 2. Task Prep (`prep-task.sh`)
- Clone repo at the PR's merge-base SHA
- Save the shipped diff for comparison
- Save task definition JSON (repo, PR number, Linear ID, ticket description, base SHA)

### 3. Task Execution (`run-task.sh --agent codex|claude`)
- Clean-room HOME (fresh temp dir each run)
- For Codex: org AGENTS.md → `$HOME/.codex/AGENTS.md`
- For Claude Code: org AGENTS.md → `$HOME/.claude/CLAUDE.md`
- Language file → repo root as `AGENTS.{lang}.md`
- Repo-specific file → repo root as `AGENTS.repo.md` (if exists)
- Clone at merge-base, inject context, launch agent with 1hr timeout
- Capture agent's git diff + event stream

### 4. Code Review Cycle

The eval imitates a real PR review loop:

**Round 1 — Initial implementation:** Agent produces first diff from the task prompt + ticket description.

**Round 2 — Review:** Spawn an Opus reviewer subagent acting as a senior engineer. Reviewer gets: ticket description, AGENTS docs, and the agent's diff. Reviewer writes substantive code review comments — not rubber stamps, not nitpicks. Focus on correctness issues, missed requirements, pattern violations, fragile approaches.

**Round 3 — Revision:** Feed review comments back to the coding agent in the same session. Agent revises its implementation. Capture the updated diff.

**Optional Round 4:** If the reviewer flagged critical issues and the revision didn't address them, one more review+revision cycle.

**Score the FINAL diff** after review cycles, not the first attempt. Optionally score both to measure improvement from review.

### 5. Scoring (subagent-based, not scripted)

Spawn an **Opus orchestrator subagent** that:

1. Spawns two scorer subagents **in parallel**:
   - **GPT-5.4** (model: `gpt54`, thinking: `extra_high`)
   - **Opus** (model: `opus`)

2. Each scorer receives:
   - The Linear ticket description (source of truth)
   - The shipped PR diff (reference implementation)
   - The agent's final diff after review cycles (what we're scoring)
   - The review comments from the reviewer (context for how the agent iterated)

3. Each scorer evaluates 5 dimensions (0-3 each):

   **a. Ticket Fidelity** — Did the agent address what the ticket asks for? Compare agent work to TICKET requirements, not to the shipped PR. If the ticket says "fix X, Y, and Z" and the agent fixed all three, that's 3/3 even if the approach differs from the shipped PR.

   **b. Correctness** — Would the agent's code actually work? Are there bugs, type errors, missing imports, broken logic? Judge the code on its own merits. Did the agent fix issues raised in review?

   **c. Scope Discipline** — Did the agent stay focused? Over-scoping (doing more than the ticket asks) is a minor penalty at most. Under-scoping (missing ticket requirements) is worse. Following ticket instructions that the shipped PR ignored is NOT a penalty.

   **d. Pattern Compliance** — Does the implementation follow the repo's existing patterns, conventions, architecture? Same framework idioms, file organization, naming.

   **e. Review Responsiveness** — Did the agent meaningfully address review feedback? Did it fix the issues raised, or ignore/misunderstand them? If no review was needed (clean first draft), score 3/3.

4. Orchestrator aggregates:
   - Average the two scores per dimension
   - Round to nearest 0.5
   - Sum for total out of 15
   - Verdict: PASS ≥ 12, PARTIAL 8-11, FAIL < 8
   - Flag any dimension where scorers disagree by 2+ points
   - Produce a plain-text summary (no markdown tables)

### Key Scoring Rules

- **Ticket is primary, PR is reference.** If the agent did something the ticket describes but the shipped PR didn't do, the agent doesn't get penalized. If the shipped PR did something not in the ticket (opportunistic cleanup, unrelated bump), the agent doesn't get penalized for missing it.
- **Approach equivalence.** Different code that achieves the same fix = full marks. We're not looking for identical diffs.
- **Over-scope is mild.** Agent hardened 8 config files when ticket said to? That's scope discipline 2/3 at worst, not 0.
- **Under-scope is severe.** Agent missed a core ticket requirement? That's ticket fidelity 1/3 or lower.

## File Layout

```
<repo-root>/
├── tasks/           # Task definition JSONs
│   └── acs-1204.json
├── scripts/
│   ├── prep-task.sh   # Clone + save shipped diff
│   └── run-task.sh    # Clean-room Codex execution
├── lang-files/        # Language-specific AGENTS files from PR #312
│   ├── lang-php.md
│   └── lang-nodejs.md
├── system-agents.md   # Org AGENTS.md from PR #312
├── logs/              # Per-task run artifacts
│   └── acs-1204/
```

Continuation:

```
│       ├── task.json
│       ├── prompt.md
│       ├── shipped.diff
│       ├── agent.diff
│       ├── agent-full.diff
│       ├── agent-commits.txt
│       ├── codex.jsonl
│       ├── codex.log
│       └── meta.json
└── results/           # Scoring output (from subagent)
```

## Agent Comparison

The harness supports `--agent codex|claude` to run the same task through both runtimes:
- Codex: `codex exec --json --full-auto` with `$HOME/.codex/AGENTS.md`
- Claude Code: `claude -p --dangerously-skip-permissions` with `$HOME/.claude/CLAUDE.md`

Same prep, same scoring, different agent — clean A/B comparison. Both use OAuth (subscription), not API keys.

## Status

- Harness scripts: working (`prep-task.sh`, `run-task.sh`)
- First run completed: ACS #1204 via Codex (663s, scored 13/15 via dual-scorer)
- Scoring subagent flow: working (Opus orchestrator + parallel GPT-5.4/Opus scorers)
- Review cycle: designed, not yet implemented in runner
- Claude Code runner path: designed, not yet implemented
- Org AGENTS.md injection fix: done (only in $HOME/.codex/ now, not repo root)
