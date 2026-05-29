# Docs/spec implementation-plan PR reviews

Use this when a PR is docs-only but the files are intended to be executable implementation plans, migration contracts, or spec checklists. Treat the docs as code contracts, not prose.

## Review focus

- **Internal dependency graph:** compare README ordering, per-spec `Depends on:` lines, sign-off gates, and install/cutover specs. If an install/cutover spec rewrites wrappers for components from later ports, it must depend on those later ports or be split/narrowed.
- **CLI/test executability:** validate pseudocode and required tests against language/runtime behavior. Example: Python `argparse` with `subparsers(required=True)` raises `SystemExit(2)` for missing subcommand; a test asserting `cli.main([]) == 2` is not runnable unless `main()` catches and returns the code.
- **Flag behavior contracts:** if a common option such as `--fixture-dir` is used in every validation command, require a defined behavior path. It should explicitly replace live integrations with fixture-backed runners/loaders or point to a separate offline test entrypoint. Otherwise documented validation may hit live services.
- **Validation predicates vs report semantics:** ensure exit codes match report intent. A report whose primary output is violations should normally render/deliver violations and exit success; reserve nonzero exit codes for structural/data-quality blockers unless the spec explicitly says delivery is intentionally suppressed.
- **Runtime/migration/autopull claims:** shell snippets must use consistent env variable names and show how secret references are resolved before clone/pull. Never copy credential values; redact actual tokens/secrets as `[REDACTED]`.
- **Checklist enforceability:** every test named in a sign-off checklist should also appear in the corresponding required-test section or validation command list.
- **Stale references:** grep for deleted/renamed spec filenames and legacy script/module names, then distinguish intentional historical references from broken links or stale instructions.
- **Current runtime truth:** compare docs/spec claims to existing wrappers, timers, README runtime tables, and scripts to catch claims such as “live,” “POC,” or “not runtime-wired.”

## Suggested quick checks

```bash
# Whitespace / markdown hygiene
git diff --check "$BASE...HEAD"

# Find legacy filenames or script names that may have gone stale
rg '00-overview|01-data-integrity|02-package-layout|03-cli-surface|04-shared-services|05-rc-runtime|06-testing-strategy|07-migration-plan|legacy_script_or_module' path/to/specs

# Inspect dependency declarations and wrapper/cutover references
rg 'Depends on:|unblocks|wrapper|systemd|cutover|retire|fixture-dir|runner_from_env|argparse|SystemExit|validate_' path/to/specs
```

For markdown local-link validation, ignore code fences and inline code spans before treating a match as a broken link; implementation specs often include sample commands with strings that look like links.

## Review-body wording pattern

When blocking a docs-only implementation-plan PR, state explicitly that the issue is an executable contract contradiction, not a prose nit:

> This is docs-only, but these specs are meant to drive coding PRs. As written, an implementer following the contract would produce an unrunnable test/live-system validation path/incorrect cutover order, so this should be fixed before the plan is locked.

## Concrete case signal

In EWA-Services/Tools #147, a docs-only consolidation-spec PR initially needed `REQUEST_CHANGES` because older heads contained executable-contract contradictions: an impossible argparse test, undefined fixture-runner behavior, inconsistent chat-space validation, forbidden-words exit-code semantics that would suppress the report output, inconsistent autopull token env names/resolution, and a P9 install dependency graph that omitted ports whose wrappers it planned to swap.

The same PR later became approve-level after those issues were fixed. Good re-review evidence for docs/spec implementation-plan PRs includes:

- GraphQL review threads show no unresolved threads, and author replies to old blockers are clear + implemented on the current diff.
- The current spec defines an offline `--fixture-dir`/`FixtureRunner` path that explicitly forbids live Greenhouse/Sheets/Notion/Chat/`op`/heartbeat calls.
- Argparse examples/tests match actual `SystemExit` behavior for missing/unknown subcommands and version/help paths.
- Report-output findings are separated from blocking structural failures (for example forbidden-words violations render and exit 0; parity/coverage failures block with exit 1).
- Runtime cutover/dependency graphs separate package-only ports, systemd wrapper swaps, and OpenClaw cron prompt edits.
- Secret-bearing autopull examples avoid token-in-URL and token-in-argv paths, then unset raw token and `GIT_CONFIG_*` material before non-git subprocesses; contract tests fail on leakage.
- Local validation can be lightweight but targeted: `git diff --check`, markdown local-link validation ignoring code spans/fences, existing relevant unit tests, and focused text probes for prior blocker contracts.
