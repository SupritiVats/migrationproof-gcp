"""Thin wrapper around google-cloud-bigquery for the migrationproof dataset."""
from functools import lru_cache
from typing import Any, Iterable

from google.cloud import bigquery

from app.config import get_settings


class BigQueryClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.project_id = settings.gcp_project_id
        self.dataset = settings.bq_dataset
        self.client = bigquery.Client(project=self.project_id)

    def table_ref(self, table_name: str) -> str:
        return f"{self.project_id}.{self.dataset}.{table_name}"

    def insert_rows(self, table_name: str, rows: Iterable[dict[str, Any]]) -> list[dict]:
        """Insert rows via the streaming insert API. Returns a list of insert errors (empty if ok)."""
        rows = list(rows)
        if not rows:
            return []
        table = self.client.get_table(self.table_ref(table_name))
        errors = self.client.insert_rows_json(table, rows)
        return errors

    def query(self, sql: str, params: list[bigquery.ScalarQueryParameter] | None = None) -> list[dict]:
        job_config = bigquery.QueryJobConfig(query_parameters=params or [])
        result = self.client.query(sql, job_config=job_config).result()
        return [dict(row.items()) for row in result]


@lru_cache
def get_bigquery_client() -> BigQueryClient:
    return BigQueryClient()
