#!/usr/bin/env bash
# Applies all DDL files in infra/bigquery/schema/ against the configured
# GCP project/dataset. Requires PROJECT_ID and BQ_DATASET env vars (or edit
# the defaults below), and an authenticated `bq` CLI.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-migrationguard-sv}"
BQ_DATASET="${BQ_DATASET:-migrationproof}"
SCHEMA_DIR="$(dirname "$0")/schema"

echo "Applying BigQuery schema to ${PROJECT_ID}:${BQ_DATASET}"

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

for sql_file in "$SCHEMA_DIR"/*.sql; do
  echo "--- Applying $(basename "$sql_file") ---"
  sed \
    -e "s/\${PROJECT_ID}/${PROJECT_ID}/g" \
    -e "s/\${BQ_DATASET}/${BQ_DATASET}/g" \
    "$sql_file" > "$TMP_FILE"
  bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false < "$TMP_FILE"
done

echo "Done. Tables in ${BQ_DATASET}:"
bq ls --project_id="${PROJECT_ID}" "${BQ_DATASET}"
