# Pending PR review integration test

INTEGRATION_TEST / LIVE_TEST marker.

Purpose: prove the queue discovery path works against live GitHub data and preserves skip behavior when credentials are unavailable.

Command:

```bash
bash scripts/list_pending_prs.sh --json --owner ewa-services --reviewer poom --limit 20
```

Skip behavior: if `gh auth status` fails or network access is unavailable, mark the integration test skipped rather than failed. The offline unit test in `scripts/test_list_pending_prs.sh` covers filtering semantics without credentials.
