# Argo CD PreSync hooks, selective sync, and image artifact compatibility

Use this reference when reviewing Infrastructure/Kubernetes PRs that add Argo CD hooks, migration Jobs, or rollout gates that depend on code shipped in an application image.

## Session pattern

In `EWA-Services/Infrastructure#4685`, the PR wrapped a staging notification Deployment and a new migration Job in one `api.yaml` Kubernetes `List`. The Job used `argocd.argoproj.io/hook: PreSync` and ran `node dist/scripts/nts-provider-migration.js staging` from the same notification image as the Deployment.

Two blockers remained even though local YAML parsing and most CI were green:

1. The notification Application still had `ApplyOutOfSyncOnly=true` in `cd/k8s/staging/applications/nts.yaml`. Argo CD selective sync does not reliably run hooks, so a `PreSync` Job under that Application may not actually gate the rollout. Moving the hook into the same YAML `List` as the Deployment does not remove the selective-sync risk.
2. The Deployment and hook Job both used `notification-service:1.20.0-staging`, but the migration changed DB state to reference `ITEXMO_BACKUP`. GitHub contents checks showed `@ewa-services/integration-nts@1.20.0` contained the migration script, while `nts/src/providers/itexmo-backup-provider.ts` first appeared in `@ewa-services/integration-nts@1.21.0`. The hook could therefore migrate DB state to a provider the rolled-out pods could not resolve.

## Review checklist

1. Identify the exact Argo CD Application owning the changed manifest and inspect its `syncPolicy.syncOptions`.
2. If the PR relies on a hook (`PreSync`, `Sync`, `PostSync`) and the Application uses `ApplyOutOfSyncOnly=true`, treat hook execution as unsafe until the PR removes/overrides selective sync or uses a non-hook mechanism guaranteed to execute.
3. Do not assume a hook is reliable just because it is in the same multi-object YAML `List` as the Deployment.
4. Verify every image tag used by both the rollout resource and hook/migration Job contains all required runtime artifacts:
   - migration script/entrypoint
   - provider/feature code consumed after migration
   - config/packaging changes needed to run the script
5. Check linked application PRs and release tags separately. A migration script and the runtime provider may land in different PRs/tags.
6. When a current inline comment already covers one blocker, reuse/cite it in the formal review instead of duplicating the same inline. For stale comments on deleted/reworked files, summarize the still-applicable issue in the formal review or place a new inline on the current file/line.

## Useful evidence commands

```bash
# Current PR state and reviews
gh pr view <PR> --repo OWNER/REPO --json headRefOid,files,comments,latestReviews,reviews

gh pr diff <PR> --repo OWNER/REPO --patch > diff.patch

gh api repos/OWNER/REPO/pulls/<PR>/comments --paginate > inline_comments.json

gh api graphql -f query='query($owner:String!,$repo:String!,$number:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$number){headRefOid reviewThreads(first:100){nodes{isResolved isOutdated comments(first:50){nodes{author{login} body path line originalLine createdAt outdated url}}}}}}}' -F owner=OWNER -F repo=REPO -F number=<PR> > review_threads.json

# Local YAML syntax fallback
ruby -e 'require "yaml"; ARGV.each { |f| YAML.load_file(f); puts "ok #{f}" }' path/to/manifest.yaml

```

Continuation:

```bash
# Verify app artifacts at exact tags; URL-encode tags containing @ or /
gh api 'repos/OWNER/APP_REPO/contents/path/to/artifact?ref=%40scope%2Fpackage%401.21.0' --jq '{path,sha,size}'
```

## Review wording pattern

- State the exact head SHA reviewed.
- Separate green local/CI checks from merge blockers.
- For image artifact blockers, name both the tag that is missing the artifact and the tag/PR where it appears.
- For selective sync, say that the hook is not a reliable rollout gate under `ApplyOutOfSyncOnly=true`, and ask for selective sync removal/override or a non-hook execution mechanism.
