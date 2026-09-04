-- Used ONLY by the benchmark harness (backend/benchmark). Never read by the
-- runtime verification engine -- that would defeat the point of the benchmark.
CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BQ_DATASET}.ground_truth` (
  scenario_id STRING NOT NULL,
  entity_id_a STRING NOT NULL,
  entity_id_b STRING NOT NULL,
  is_dependency BOOL NOT NULL,
  expected_wave_conflict BOOL NOT NULL,
  failure_type STRING,          -- e.g. cross_wave_dependency | stale_dns | hidden_dependency | none
  expected_decision STRING      -- ALLOW | BLOCK, for the scenario's target wave
);
