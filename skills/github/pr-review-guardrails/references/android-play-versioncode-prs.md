# Android Play Store `versionCode` PR reviews

Use this when a PR changes Android Gradle `versionCode` generation, CI release versioning, Play Store track rollout sequencing, or removes `GITHUB_RUN_NUMBER` / workflow-run-derived build numbers.

## Review checks

1. **Play monotonicity across all tracks**
   - Play requires every uploaded artifact to have a `versionCode` greater than any existing code on any relevant track.
   - Check the stated current max live/internal/closed/prod codes from the PR/ticket, not only the next release example.
   - If internal/staging runs have previously uploaded higher codes than production, the production code after the fix must exceed that max.

2. **No workflow-run drift**
   - Removing `GITHUB_RUN_NUMBER` or other per-workflow counters is usually the right direction when internal and production workflows build the same tag separately.
   - Verify both workflows/flavors derive from the same deterministic semantic version inputs unless a documented explicit override such as `VERSION_CODE` remains for hotfixes.

3. **Monotonic formula over future semver**
   - Test more than the next release. Probe at least:
     - current/next minor, e.g. `1.391.0`, `1.392.0`
     - next patch, e.g. `1.392.1`
     - next major, e.g. `2.0.0`
   - A formula like `major*10000 + minor*100 + patch + offset` can still decrease on the next major version if the offset dominates the scale; treat that as blocking.

4. **Flavor/track collision check**
   - If staging/internal and production both upload to Play for the same semantic version, they need unique codes.
   - Reserve digits/space for flavor after scaling semver, for example `scaledSemver * 10 + flavorOffset`, rather than adding flavor offsets directly to an unscaled patch value.
   - Check patch+1 staging does not collide with prior patch production (for example `1.392.1` staging vs `1.392.0` production).

5. **Gradle placement and flavor behavior**
   - If `defaultConfig.versionCode` is removed and flavor-level `versionCode` values are introduced, verify every Play-uploaded flavor has a value.
   - Search for `applicationIdSuffix`, flavor-specific application IDs, and release workflow selection so you know whether codes share one Play package or separate apps/tracks.

6. **Docs / rollout instructions**
   - PR descriptions often contain earlier arithmetic examples. If the final implementation changed (for example from `51100` to `13912001`), note stale examples as a non-blocking operator-doc follow-up unless they would cause an unsafe manual rollout.
   - Check the after-merge rollout instruction: discard blocked drafts, build from a tag containing the fix, and confirm the produced code exceeds the current max.

## Validation snippets

For a quick current-file arithmetic probe, model the Gradle formula in Python and print staging/production codes for representative versions. Record it in the review body or memory when it informed the verdict.

```python
def code(v, flavor_offset):
    major, minor, patch = map(int, v.split('.'))
    scaled = (major * 1_000_000 + minor * 1_000 + patch) * 10
    return scaled + flavor_offset

for v in ['1.391.0', '1.392.0', '1.392.1', '2.0.0']:
    print(v, code(v, 0), code(v, 1))
```

## Verdict guidance

- **Request changes** when the formula can decrease on a future major bump, can collide between staging/internal and production, or does not exceed the known current Play max.
- **Approve** when the formula is deterministic, monotonic across representative semver transitions, unique per Play-uploaded flavor/track, and the remaining red checks are only process/metadata gates unrelated to code safety.
- Treat inability to run local Gradle because the host lacks Java/Android tooling as an environment limitation; rely on current remote CI plus local diff/arithmetic validation when sufficient.
