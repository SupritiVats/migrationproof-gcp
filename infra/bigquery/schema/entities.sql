CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BQ_DATASET}.entities` (
  entity_id STRING NOT NULL,
  name STRING NOT NULL,
  type STRING NOT NULL,          -- service | database | vm | dns | external_api
  metadata JSON,
  source_artifact STRING,
  scenario_id STRING,
  created_at TIMESTAMP NOT NULL
);
