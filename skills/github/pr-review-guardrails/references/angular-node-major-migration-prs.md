# Angular / Node major-version migration PR reviews

Use this reference when a PR migrates an Angular/Ionic frontend major version, updates Node runtime pins, or claims to satisfy a ticket such as “Angular 19+ / Node 22+”. Treat these as runtime-contract migrations, not simple dependency bumps.

## Checklist

1. **Ticket / DoD alignment is blocking evidence**
   - Fetch the linked ticket and quote the exact acceptance criteria / Definition of Done.
   - Compare the PR title, package versions, `engines.node`, CI `node-version`, `.mise.toml`/devcontainer/runtime pins, and lockfile versions against the ticket.
   - If the ticket says “Angular 19+” and “Node 22+” but the PR ships Angular 18 / Node 20, request changes unless the PR/ticket contains an explicit accepted scope change.
   - Passing CI does not override a mismatch with the accepted migration scope.

2. **Node version consistency**
   - Check `package.json` `engines.node`, `package-lock.json` package engine requirements, GitHub Actions setup-node pins, devcontainer/mise/tooling pins, and deploy/runtime images where visible.
   - Do not treat a partial Node update as sufficient for a runtime migration ticket. Align package/runtime/CI pins to one supported version family.

3. **CI install/build/test evidence**
   - For dependency migrations, distinguish stale failures from current head failures. Re-check current `gh pr checks` and current lockfile before carrying forward an old install blocker.
   - Common resolved/stale findings include peer-dependency install failures, missing lockfile packages, invalid JSON comments in config files, and fakeAsync timer leaks after the author force-pushes fixes.
   - If frontend CI now passes, do not keep older install/test blockers unless current code evidence still reproduces them.

4. **Browser support / CSS feature compatibility**
   - If `.browserslistrc` or target browsers are broadened, search for modern CSS features already used by the app (for example `:has(...)`).
   - A lower browser floor can be request-changes-level when the app relies on features unsupported by newly admitted versions and no fallback exists.
   - Require either a compatible browser floor or a non-feature fallback before approving broadened support.

5. **Sonar/test classification**
   - New test helpers under directories like `src/testing/**` can be counted as source if `sonar.test.inclusions` only includes `**/*.test.ts` or similar.
   - If current Sonar checks pass, treat old classification/coverage comments as resolved; otherwise require updating Sonar test/coverage globs or moving helpers under test-included paths.

## Example review shape

- “FE-2321 DoD requires Angular 19+ and Node v22+, but current head remains on Angular 18.2.x and Node 20 (`package.json` engines plus CI `node-version`). Please either retarget the implementation to Angular 19+/Node 22+ across package/runtime/CI pins or provide an explicit accepted scope change.”
- “`.browserslistrc` now admits browser versions without `:has()` support while `src/global.scss` relies on `ion-app.ion-page:has(...)`; raise the floor or add a fallback.”

## Pitfall

Do not over-index on a stale prior `CHANGES_REQUESTED` body. Re-read current PR comments, review threads, current checks, and current lockfile/package summary. Mark resolved findings explicitly, then block only on current code/ticket evidence.
