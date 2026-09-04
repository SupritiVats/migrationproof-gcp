CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BQ_DATASET}.migration_waves` (
  wave_id STRING NOT NULL,
  wave_number INT64 NOT NULL,
  entity_id STRING NOT NULL,
  scenario_id STRING NOT NULL
);
