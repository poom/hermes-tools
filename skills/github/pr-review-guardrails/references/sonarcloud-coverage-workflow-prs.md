# SonarCloud coverage workflow PRs

Use this reference when reviewing PRs that add or consolidate SonarCloud coverage workflows for Python/serverless repos.

## Review pattern

1. Verify the workflow is the intended single coverage owner, or that any duplicated test/coverage jobs have a documented purpose.
2. Check workflow `paths:` cover every input that can change what the Sonar/coverage job runs or reports:
   - service source directories
   - `tests/**`
   - `Makefile` or other test entrypoints
   - requirements/lock files used by the job
   - `.coveragerc`
   - `sonar-project.properties`
   - the workflow file itself
3. Confirm dependency/auth setup happens before the test entrypoint if `make test` installs private GitHub dependencies. A green remote job can be stronger evidence than an ad hoc local isolated run when the host lacks private packages.
4. Align the three coverage surfaces:
   - `.coveragerc` `source = ...`
   - pytest/coverage `--cov=...` flags or equivalent
   - `sonar.sources`, `sonar.tests`, `sonar.test.inclusions`, and `sonar.python.coverage.reportPaths`
5. If integration tests require Docker Compose, verify teardown is guaranteed with a shell `trap` or equivalent cleanup on any exit.
6. Read prior review threads for path-glob and coverage-topology issues. If the current head deleted/replaced older workflows or property files, mark older inline findings stale/resolved rather than repeating them.

## Local verification notes

- Run focused newly added tests when practical.
- Run changed-file lint/format for Python files.
- Parse workflow YAML locally. If `actionlint` is unavailable, Ruby stdlib YAML is a lightweight fallback:
  ```bash
  ruby -e 'require "yaml"; ARGV.each { |f| YAML.load_file(f); puts "ok #{f}" }' .github/workflows/name.yaml
  ```
- If the full local test glob fails only because an isolated host cannot fetch/import a private internal dependency, record the exact limitation and rely on current-head remote CI for that dependency path. Do not turn this into a code blocker when CI proves the repo's configured environment works.

## Common non-blocking caveats

- Explicit test globs (for example `test_accial_*`, `test_clevertap_*`) require future updates when new suites do not match the naming pattern.
- Removing a `SONAR_TOKEN` guard can make secret-unavailable/fork runs fail instead of skip. If current required CI has the token and passes, this is usually a caveat, not a blocker.
- Policy-bot or branch freshness may still block merge after code approval; report these as process gates separately from code findings.
