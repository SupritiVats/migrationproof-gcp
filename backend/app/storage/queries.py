"""Shared BigQuery query helpers for fetching a project/scenario's graph data.

Used by both the FastAPI /verify endpoint and the offline benchmark harness,
so "production" and "benchmark" always read data the exact same way.
"""
from __future__ import annotations

from google.cloud import bigquery

from app.models.schemas import Dependency, DependencyStatus, Entity, Evidence
from app.storage.bigquery_client import BigQueryClient, get_bigquery_client


def _param(name: str, value: str) -> bigquery.ScalarQueryParameter:
    return bigquery.ScalarQueryParameter(name, "STRING", value)


def _array_param(name: str, values: list[str]) -> bigquery.ArrayQueryParameter:
    return bigquery.ArrayQueryParameter(name, "STRING", values)


def fetch_project_graph_data(
    project_id: str, bq: BigQueryClient | None = None
) -> tuple[list[Entity], list[Dependency], dict[str, list[Evidence]], dict[str, int]]:
    """Returns (entities, verified dependencies, evidence-by-dependency-id, wave_of)."""
    bq = bq or get_bigquery_client()

    entity_rows = bq.query(
        f"SELECT entity_id, name, type, source_artifact FROM `{bq.table_ref('entities')}` "
        f"WHERE scenario_id = @project_id",
        params=[_param("project_id", project_id)],
    )
    dependency_rows = bq.query(
        f"SELECT dependency_id, source_entity_id, target_entity_id, dependency_type, status "
        f"FROM `{bq.table_ref('dependencies')}` WHERE scenario_id = @project_id AND status = 'verified'",
        params=[_param("project_id", project_id)],
    )
    dependency_ids = [d["dependency_id"] for d in dependency_rows]
    evidence_rows = []
    if dependency_ids:
        evidence_rows = bq.query(
            f"SELECT evidence_id, dependency_id, artifact_uri, artifact_type, quoted_snippet, extracted_by "
            f"FROM `{bq.table_ref('evidence')}` WHERE dependency_id IN UNNEST(@dependency_ids)",
            params=[_array_param("dependency_ids", dependency_ids)],
        )
    wave_rows = bq.query(
        f"SELECT entity_id, wave_number FROM `{bq.table_ref('migration_waves')}` WHERE scenario_id = @project_id",
        params=[_param("project_id", project_id)],
    )

    entities = [
        Entity(entity_id=r["entity_id"], name=r["name"], type=r["type"], source_artifact=r.get("source_artifact"))
        for r in entity_rows
    ]
    dependencies = [
        Dependency(
            dependency_id=r["dependency_id"],
            source_entity_id=r["source_entity_id"],
            target_entity_id=r["target_entity_id"],
            dependency_type=r["dependency_type"],
            status=DependencyStatus(r["status"]),
        )
        for r in dependency_rows
    ]
    evidence_by_dependency: dict[str, list[Evidence]] = {}
    for r in evidence_rows:
        ev = Evidence(
            evidence_id=r["evidence_id"],
            dependency_id=r["dependency_id"],
            artifact_uri=r["artifact_uri"],
            artifact_type=r["artifact_type"],
            quoted_snippet=r["quoted_snippet"],
            extracted_by=r["extracted_by"],
        )
        evidence_by_dependency.setdefault(ev.dependency_id, []).append(ev)
    wave_of = {r["entity_id"]: r["wave_number"] for r in wave_rows}

    return entities, dependencies, evidence_by_dependency, wave_of
