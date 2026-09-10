"""Orchestrator: runs Discovery -> Evidence for a project's artifacts and
writes the resulting entities/dependencies/evidence to BigQuery.

This is the pipeline that Phase 4 wires up to replace the hand-seeded
`scripts/load_scenario_to_bigquery.py` data with real Gemini extraction.
The deterministic verification engine (app/verification) never calls Gemini
directly -- it only ever reads from BigQuery, regardless of whether the data
came from this orchestrator or the synthetic seed script.
"""
from __future__ import annotations

import datetime
import uuid

from app.agents.discovery_agent import run_discovery
from app.agents.evidence_agent import run_evidence
from app.agents.gemini_client import GeminiClient
from app.storage.bigquery_client import get_bigquery_client
from app.storage.gcs_client import get_gcs_client


def run_discovery_pipeline(project_id: str) -> dict:
    """Fetch a project's raw artifacts from GCS, run Discovery + Evidence,
    and persist candidate/verified entities+dependencies+evidence to BigQuery.

    Dependencies with zero supporting evidence are discarded before they ever
    reach BigQuery (and therefore can never influence a verification decision).
    Dependencies WITH evidence are marked status='verified' -- "verified" here
    means "backed by at least one cited artifact", not "guaranteed correct";
    the deterministic rules engine still applies confidence thresholds on top.
    """
    gcs = get_gcs_client()
    bq = get_bigquery_client()
    client = GeminiClient()

    artifact_uris = [
        uri for uri in gcs.list_artifacts(project_id)
        # reference_data.json is the synthetic generator's ground-truth file,
        # not a real infrastructure artifact -- never feed it to the agents.
        if not uri.endswith("reference_data.json")
    ]
    if not artifact_uris:
        raise ValueError(f"No artifacts found for project '{project_id}'. Upload artifacts first.")

    artifacts = {uri.rsplit("/", 1)[-1]: gcs.download_text(uri) for uri in artifact_uris}

    discovery = run_discovery(artifacts, scenario_id=project_id, client=client)
    evidence_output = run_evidence(discovery.dependencies, artifacts, scenario_id=project_id, client=client)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    entity_rows = [
        {
            "entity_id": e.entity_id,
            "name": e.name,
            "type": e.type.value,
            "metadata": None,
            "source_artifact": None,
            "scenario_id": project_id,
            "created_at": now,
        }
        for e in discovery.entities
    ]

    dependency_rows = []
    evidence_rows = []
    evidence_by_pair = {(de.source_entity_id, de.target_entity_id): de.evidence for de in evidence_output.dependency_evidence}

    for dep in discovery.dependencies:
        key = (dep.source_entity_id, dep.target_entity_id)
        evidence_items = evidence_by_pair.get(key, [])
        if not evidence_items:
            continue  # no evidence -> dropped, never reaches the verification engine

        dependency_id = f"{project_id}::dep::{dep.source_entity_id}->{dep.target_entity_id}"
        dependency_rows.append(
            {
                "dependency_id": dependency_id,
                "source_entity_id": dep.source_entity_id,
                "target_entity_id": dep.target_entity_id,
                "dependency_type": dep.dependency_type,
                "confidence": None,  # computed at verification time from evidence, not stored here
                "status": "verified",
                "scenario_id": project_id,
                "created_at": now,
            }
        )
        for i, item in enumerate(evidence_items):
            evidence_rows.append(
                {
                    "evidence_id": f"{dependency_id}::ev{i}",
                    "dependency_id": dependency_id,
                    "artifact_uri": f"gs://project/{project_id}",
                    "artifact_type": item.artifact_type,
                    "quoted_snippet": item.quoted_snippet,
                    "extracted_by": "evidence_agent",
                    "created_at": now,
                }
            )

    bq.insert_rows("entities", entity_rows)
    bq.insert_rows("dependencies", dependency_rows)
    bq.insert_rows("evidence", evidence_rows)

    return {
        "project_id": project_id,
        "entities_discovered": len(entity_rows),
        "dependencies_verified": len(dependency_rows),
        "dependencies_dropped_no_evidence": len(discovery.dependencies) - len(dependency_rows),
        "evidence_records": len(evidence_rows),
    }
