# FINN-Web-App: GrowthBook experiment pattern and push fallback

Session source: FE-2470 (`Redirect authenticated users away from landing page`) in `EWA-Services/FINN-Web-App`.

## GrowthBook / experiment key pattern

FINN-Web-App's `src/app/experiments/experiment-keys.index.ts` header says new experiment keys should be added only through the experiment schematic. For boolean GrowthBook flags, feature code should consume a generated `*ExperimentKeyService` wrapper rather than calling `ExperimentService` directly from guards/components/services.

Correct pattern observed:

1. Add the key to `EXPERIMENT_KEYS` with the correct typed default, e.g. boolean fallback `false`.
2. Add a generated-style service under `src/app/experiments/<slug>/<slug>.service.ts`.
3. The generated service wraps `ExperimentService` and exposes methods such as:
   - `get()`
   - `value$()`
   - `valueWhenReady$()`
   - `isOn()`
   - `whenOn()`
4. Inject the generated service in application code.
5. Keep flag OFF/control behavior identical to previous behavior.
6. Add tests for flag ON, flag OFF, anonymous/authenticated or other relevant variants, and safe fallback on flag lookup errors when applicable.

Anti-pattern corrected in FE-2470 (first round):

```ts
// Avoid in app feature code when a generated key service is expected.
this.experimentService.valueWhenReady$(KEY, EXPERIMENT_KEYS[KEY])
```

Preferred wrapper-consumption shape:

```ts
private readonly redirectAuthenticatedLandingUsersExperiment = inject(
  RedirectAuthenticatedUsersAwayFromLandingPageExperimentKeyService
);

return this.redirectAuthenticatedLandingUsersExperiment.value$().pipe(...);
```

### Guard/cold-start readiness caveat

For guards or other one-shot decision points that call `take(1)`, the generated wrapper must not expose an immediate fallback stream backed by `ExperimentService.value$()`. `value$()` emits the compile-time fallback before GrowthBook initialization, so a cold app load can incorrectly lock in `false` before the SDK resolves the actual ON cohort value.

Safe generated-service shape for guard-critical flags:

```ts
/** Reactive stream of the experiment key value after GrowthBook is ready */
value$(): Observable<boolean> {
  return this.valueWhenReady$();
}

/** Read the experiment key only after GrowthBook initialization completes. */
valueWhenReady$(): Observable<boolean> {
  return this.experimentService.valueWhenReady$(
    RedirectAuthenticatedUsersAwayFromLandingPageExperimentKeyService.KEY,
    EXPERIMENT_KEYS[
      "POOM-FE-2470-Redirect-authenticated-users-away-from-landing-page"
    ],
    { refreshOnSubscribe: true }
  );
}
```

Then the guard can use the wrapper without consuming the fallback too early:

```ts
return this.redirectAuthenticatedLandingUsersExperiment.valueWhenReady$().pipe(
  take(1),
  switchMap((redirectAuthenticatedUsers) => { ... })
);
```

Add a deterministic spec with a `Subject<boolean>` proving that Firebase/auth or other side-effectful decision logic is not called until the ready-gated flag emits. This catches the exact `fallback false -> resolved true` cold-start bug that reviewer feedback found.

### GrowthBook audit pitfall: flag-OFF must not wait or broaden route behavior

The automated GrowthBook implementation review treats any route-activation delay or always-on guard execution as a flag-safety failure, even if the guard eventually falls back to old behavior. In FE-2470 follow-up work, these approaches failed the audit:

- Adding the existing `LandingGuard` to `:country/:campaign` routes. This broadened landing canonicalization/preload/profile-country behavior to campaign routes outside the FE-2470 flag.
- Adding a dedicated campaign-route guard that always returned an `Observable` from `valueWhenReady$()` with a 5s timeout. The audit considered the flag-OFF path changed because route activation could now wait up to 5s.
- Changing that dedicated guard to return `true` immediately while subscribing and navigating later. The audit considered this a race with `CampaignLandingGuard` and new execution behavior outside the guarded route-resolution path.

For route guards, design the implementation so the flag-OFF/control path is literally unchanged: no new wait, no new guard side effect, no added canonicalization/preload, and no asynchronous navigation race. If a new URL shape (for example both `/landing/:country` and `/landing/:country/:campaign`) must be covered by the same experiment, prefer a shared guard path that can make the full redirect decision synchronously from already-ready state, or refactor so the existing route path owns the experiment decision without delaying/control-path behavior. If that is not possible, stop and ask for product/engineering direction rather than pushing a workaround that the GrowthBook audit will reject.

Additional FE-2470 audit finding: do **not** fix guard cold-start readiness by adding an unconditional app-initializer wait on landing routes. The GrowthBook audit rejected `ApplicationInitializerFactory` waiting for initial experiments on landing routes because it added a new startup dependency/timing behavior even when the FE-2470 flag was OFF. Any readiness dependency must itself be inside the flagged/treatment path or otherwise already existing behavior.

## Schematic caveat

The repo includes `link-experiment-schematics.sh` and an `npm run experiment-generate` flow. In the FE-2470 checkout, linking/running the schematic was blocked because `.mise.toml` was untrusted. Do not blindly change trust settings unless the user has asked for environment changes. If blocked, copy the generated service shape exactly from the schematic template or a nearby existing generated service, then validate with repo checks.

Useful files to inspect:

- `experiment-service-schematics/src/experiment-service-schematics/files/__fileName__.service.ts.template`
- `experiment-service-schematics/src/experiment-service-schematics/index.ts`
- Existing generated services under `src/app/experiments/*/*.service.ts`

## Validation used for FE-2470

Targeted checks that caught/fixed the pattern issue:

```bash
npx prettier --check <changed-ts-files>
npx tsc-files --noEmit --pretty <changed-ts-files>
git diff --check
npx ng test --include src/app/guards/landing.guard.spec.ts --watch=false --browsers=ChromeHeadless
```

Note: the focused Karma run can print `Some of your tests did a full page reload!` after `TOTAL: 17 SUCCESS` while still exiting `0`. Treat the exit code plus successful spec count as the local result, while noting the warning.

## Git push hang fallback

During FE-2470, repeated `git push` attempts timed out/hung with no output even after non-interactive/traced/PTY variants. Safe sequence used:

1. Verify no stuck git process:

```bash
ps -axo pid,ppid,stat,command | grep -E 'git|ssh|gh' | grep -v grep || true
```

2. Compare local and remote heads:

```bash
git rev-parse HEAD
git ls-remote origin <branch>
```

3. If push remains unusable, update the PR branch through GitHub Git Data API.

   For incremental fixes on an already-open PR, use the current remote PR head as the parent so history remains append-only. For a requested rebase/force-push, first rebase locally onto `origin/main`, then create the API commit with `origin/main` as the single parent and PATCH the branch ref with `force: true`. Build the tree from `git diff --name-status origin/main...HEAD` so the API commit contains the full rebased PR diff, not only the last local commit.

   The API sequence is:
   - read current remote branch SHA
   - read the chosen parent commit/tree (`origin/main` for force-updated rebases, remote branch head for append-only fixes)
   - create blobs/tree from corrected local files
   - create a commit with the chosen parent SHA
   - PATCH the branch ref to the new commit SHA (`force: true` only when intentionally rebasing/force-updating)

4. Immediately align the local checkout afterward:

```bash
git fetch origin <branch>
git reset --hard origin/<branch>
git status --short
git rev-parse HEAD
```

Pitfall: API-created commit SHA will differ from local amended commit SHA even if file content/message are equivalent. Always fetch/reset so future work starts from the actual PR head.

## GitHub review threads: finding and resolving unresolved comments

When the user says there are unresolved comments, do not rely only on `gh pr view --json reviews,comments` or `repos/{owner}/{repo}/pulls/{pr}/comments`; those list comments/reviews but not thread resolution state. Query review threads with GraphQL:

```bash
OWNER_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
OWNER=${OWNER_REPO%/*}; REPO=${OWNER_REPO#*/}; PR=<number>
gh api graphql \
  -f owner="$OWNER" -f name="$REPO" -F number="$PR" \
  -f query='query($owner:String!, $name:String!, $number:Int!) { repository(owner:$owner, name:$name) { pullRequest(number:$number) { reviewThreads(first:100) { totalCount pageInfo { hasNextPage endCursor } nodes { id isResolved isOutdated path line comments(first:20) { nodes { author { login } body url createdAt } } } } } } }' \
  > /tmp/pr-review-threads.json
```

Inspect every `isResolved: false` thread. After the fix is pushed or a thread is obsolete/outdated and genuinely addressed, resolve it with:

```bash
gh api graphql \
  -f threadId='<PRRT_...>' \
  -f query='mutation($threadId:ID!){ resolveReviewThread(input:{threadId:$threadId}) { thread { id isResolved } } }'
```

Verify afterward by re-querying `reviewThreads` and counting unresolved nodes. Avoid piping raw `gh` output directly into `python`/interpreters; write JSON to a temp file first and then parse it.
