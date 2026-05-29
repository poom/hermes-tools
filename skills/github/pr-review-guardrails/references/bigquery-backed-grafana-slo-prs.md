# BigQuery-backed Grafana SLO PR reviews

Use this when a Terraform PR adds Grafana SLOs whose SLI queries are raw BigQuery / `grafana_queries` rather than Prometheus-style ratio/freeform queries.

## Review checklist

1. **Population alignment**
   - Numerator and denominator must describe the same base population.
   - Do not let denominator filters exclude the worst failures. Example: latency `Total` should not drop completed requests with `latency >= 3600s` unless those rows are proven invalid/corrupt telemetry and the invalid-row contract is documented.
   - If outlier caps are needed for corrupt data, prefer explicit invalid-row predicates (missing timestamps, negative durations, impossible future timestamps) rather than silently excluding slow-but-valid attempts.

2. **Terminal-state semantics**
   - Firestore/CDC export tables can contain multiple `UPDATE` rows per logical object/attempt.
   - Correctness SLIs that count rows with `error IS NULL` should also prove they are counting terminal/final OCR documents, not intermediate updates that are still in flight.
   - Look for status fields, completed timestamps, final-result fields, latest-row selection, or ticket/product evidence that each matching row is terminal.

3. **Window semantics**
   - Check whether the SQL query hard-codes a rolling lookback (`timestamp >= CURRENT_TIMESTAMP() - INTERVAL 7 DAY`) while the Grafana SLO objective also sets `window = "7d"`.
   - This can produce a rolling aggregate sampled into another rolling objective window instead of a normal event/population SLI.
   - Ask the author to confirm this is the intended Grafana SLO pattern or let the SLO objective/window own the time bound.

4. **Environment/data-source assumptions**
   - Hard-coded production datasets in Terraform that can be planned/applied from staging/dev should be intentional and documented.
   - Verify datasource UID/type and destination datasource match existing Grafana architecture.

5. **Plan evidence remains required**
   - For Terraform-managed SLO resources, inspect a current Digger/Terraform plan before final approval/apply/merge.
   - If Digger is blocked by a project lock, source review can still identify code blockers, but report merge readiness as blocked until the plan is posted and reviewed.
   - Missing plan evidence by itself may justify `COMMENT` when source is otherwise clean; if source-level SLI defects exist, `REQUEST_CHANGES` is appropriate.

## Example blocker wording

```markdown
The latency SLI denominator excludes any completed OCR record whose `updatedAt - createdAt` is `>= 3600` seconds. Those are the worst latency failures, so dropping them from both numerator and denominator can inflate the SLO. Please count them as failures by using the same base population for `Total`, or document/prove that these rows are invalid telemetry and filter only invalid rows explicitly.
```
