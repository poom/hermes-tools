# GitHub Actions Docker production promotion review note

Use this reference when reviewing PRs that modify reusable GitHub Actions workflows for Node/npm publishing, staging deploys, and optional Docker image deployment.

## Durable pitfall

If the PR adds a branch where release/staging deploys can choose between:
- legacy npm-package infrastructure deployment (for repositories without Docker config), and
- Docker image build/push/deploy (for repositories with a Make/script config hook),

then the manual production deploy path must make the same deploy-mode decision. Do not approve a production workflow that always calls the legacy npm deploy action if Docker-enabled repositories are expected to promote the already-built image.

## What to inspect

1. Find the release/staging workflow path that resolves Docker config, builds/pushes the image, and dispatches deployment.
2. Find the manual production deploy workflow.
3. Verify production does **deploy-only promotion** for Docker-enabled repositories:
   - it reuses or mirrors Docker config resolution,
   - it validates/uses the released package version as the Docker tag,
   - it dispatches the Docker deploy event/action (for example `docker-image-published`) rather than `npm-package-published`,
   - it does not publish to npm again.
4. Verify non-Docker repositories still use the legacy npm-package deploy path.

## Review wording pattern

Blocking: this manual production workflow always calls the legacy npm deployment action, but release/staging can opt into Docker image deployment. Docker-enabled apps would publish/build/deploy the image to staging, then have no matching production promotion path. Please mirror the Docker config resolution/deploy-only path here, or factor out a reusable deploy-only workflow that chooses Docker vs npm consistently without publishing again.

## Thread hygiene

When a previously posted blocker is fixed on the current diff, resolve that stale thread before posting the new review. Do not repeat an outdated blocker just because it is still visible in existing review history.
