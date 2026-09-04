CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BQ_DATASET}.evidence` (
  evidence_id STRING NOT NULL,
  dependency_id STRING NOT NULL,
  artifact_uri STRING NOT NULL,
  artifact_type STRING NOT NULL, -- application_config | dns_record | network_connection | architecture_doc | vm_inventory | service_catalog
  quoted_snippet STRING NOT NULL,
  extracted_by STRING NOT NULL,  -- agent name, e.g. evidence_agent
  created_at TIMESTAMP NOT NULL
);
