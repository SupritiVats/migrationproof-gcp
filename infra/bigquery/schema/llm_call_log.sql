-- Cost/audit tracking for every Gemini/ADK call made by the agents.
CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BQ_DATASET}.llm_call_log` (
  call_id STRING NOT NULL,
  agent STRING NOT NULL,          -- discovery_agent | evidence_agent | analysis_agent
  model STRING NOT NULL,
  scenario_id STRING,
  prompt_tokens INT64,
  completion_tokens INT64,
  latency_ms INT64,
  success BOOL,
  error_message STRING,
  created_at TIMESTAMP NOT NULL
);
