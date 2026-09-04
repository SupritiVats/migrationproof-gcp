CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BQ_DATASET}.dependencies` (
  dependency_id STRING NOT NULL,
  source_entity_id STRING NOT NULL,
  target_entity_id STRING NOT NULL,
  dependency_type STRING NOT NULL,
  confidence FLOAT64,
  status STRING NOT NULL,        -- candidate | verified | rejected
  scenario_id STRING,
  created_at TIMESTAMP NOT NULL
);
