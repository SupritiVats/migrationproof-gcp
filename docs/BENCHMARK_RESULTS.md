# MigrationProof Benchmark Results

> **Note:** These results benchmark the deterministic verification engine
> against hand-seeded reference data (entities/dependencies/evidence loaded
> directly via `scripts/load_scenario_to_bigquery.py`), not yet the full
> Gemini/ADK Discovery+Evidence extraction pipeline (Phase 4). Once a Gemini
> API key is configured and the agents populate these same BigQuery tables
> from raw artifacts, re-run this benchmark for true end-to-end numbers.

Scenarios evaluated: **8**

| Metric | Value |
|---|---|
| Overall decision accuracy | 100.0% |
| Unsafe-approval rate (BLOCK expected, ALLOW given) | 0.0% |
| False-block rate (ALLOW expected, BLOCK given) | 0.0% |
| Contradiction-detection accuracy | 100.0% |

## Per-scenario results

| Scenario | Failure type | Expected | Actual | Confidence | Result |
|---|---|---|---|---|---|
| scn-01-safe-migration | none | ALLOW | ALLOW | 0.61 | PASS |
| scn-02-db-migrated-after-app | cross_wave_dependency | BLOCK | BLOCK | 0.90 | PASS |
| scn-03-stale-dns-reference | contradictory_evidence | BLOCK | BLOCK | 0.90 | PASS |
| scn-04-hidden-dependency-in-config | low_confidence_dependency | ALLOW | ALLOW | 0.56 | PASS |
| scn-05-forgotten-external-dependency | none | ALLOW | ALLOW | 0.61 | PASS |
| scn-06-incompatible-waves-two-services | cross_wave_dependency | BLOCK | BLOCK | 0.90 | PASS |
| scn-07-stale-inventory-no-impact | none | ALLOW | ALLOW | 0.61 | PASS |
| scn-08-contradictory-evidence-queue | contradictory_evidence | BLOCK | BLOCK | 0.90 | PASS |
