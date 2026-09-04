CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BQ_DATASET}.verification_results` (
  result_id STRING NOT NULL,
  scenario_id STRING NOT NULL,
  wave_number INT64 NOT NULL,
  decision STRING NOT NULL,      -- ALLOW | BLOCK
  reasons JSON,
  confidence FLOAT64 NOT NULL,
  blast_radius JSON,
  narrative STRING,
  created_at TIMESTAMP NOT NULL
);
