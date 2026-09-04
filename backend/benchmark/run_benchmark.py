"""Run the deterministic verification engine against every synthetic scenario
stored in BigQuery and compare its decision to the known ground truth.

This is the benchmark referenced in README Phase 7. It currently reads
entities/dependencies/evidence that were seeded directly from the synthetic
generator's reference data (see scripts/load_scenario_to_bigquery.py). Once
the Discovery + Evidence agents (Phase 4) are wired up with a real Gemini
key, point this at their output instead (same BigQuery tables, same schema)
for a true end-to-end benchmark of the full pipeline.

Usage:
    python -m benchmark.run_benchmark
"""
from __future__ import annotations

import datetime
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import Decision, Dependency, DependencyStatus, Entity, Evidence  # noqa: E402
from app.storage.bigquery_client import get_bigquery_client  # noqa: E402
from app.verification.rules import RuleContext, run_verification  # noqa: E402
from benchmark.metrics import BenchmarkReport, ScenarioOutcome  # noqa: E402
from scripts.scenario_definitions import SCENARIOS  # noqa: E402

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"


def fetch_scenario_graph_data(scenario_id: str):
    bq = get_bigquery_client()

    entity_rows = bq.query(
        f"SELECT entity_id, name, type, source_artifact FROM `{bq.table_ref('entities')}` "
        f"WHERE scenario_id = @scenario_id",
        params=[_param("scenario_id", scenario_id)],
    )
    dependency_rows = bq.query(
        f"SELECT dependency_id, source_entity_id, target_entity_id, dependency_type, status "
        f"FROM `{bq.table_ref('dependencies')}` WHERE scenario_id = @scenario_id AND status = 'verified'",
        params=[_param("scenario_id", scenario_id)],
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
        f"SELECT entity_id, wave_number FROM `{bq.table_ref('migration_waves')}` WHERE scenario_id = @scenario_id",
        params=[_param("scenario_id", scenario_id)],
    )

    entities = [Entity(entity_id=r["entity_id"], name=r["name"], type=r["type"], source_artifact=r.get("source_artifact")) for r in entity_rows]
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


def _param(name: str, value: str):
    from google.cloud import bigquery

    return bigquery.ScalarQueryParameter(name, "STRING", value)


def _array_param(name: str, values: list[str]):
    from google.cloud import bigquery

    return bigquery.ArrayQueryParameter(name, "STRING", values)


def persist_result(scenario_id: str, target_wave: int, result) -> None:
    bq = get_bigquery_client()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    row = {
        "result_id": str(uuid.uuid4()),
        "scenario_id": scenario_id,
        "wave_number": target_wave,
        "decision": result.decision.value,
        "reasons": json.dumps([r.model_dump() for r in result.reasons]),
        "confidence": result.confidence,
        "blast_radius": json.dumps(result.blast_radius_by_entity),
        "narrative": None,
        "created_at": now,
    }
    bq.insert_rows("verification_results", [row])


def main() -> None:
    from app.verification.graph import DependencyGraph

    outcomes: list[ScenarioOutcome] = []

    for scenario in SCENARIOS:
        entities, dependencies, evidence_by_dependency, wave_of = fetch_scenario_graph_data(scenario.scenario_id)
        graph = DependencyGraph.build(entities, dependencies)
        ctx = RuleContext(
            graph=graph,
            wave_of=wave_of,
            evidence_by_dependency=evidence_by_dependency,
            target_wave=scenario.target_wave,
        )
        result = run_verification(ctx)
        persist_result(scenario.scenario_id, scenario.target_wave, result)

        outcomes.append(
            ScenarioOutcome(
                scenario_id=scenario.scenario_id,
                expected_decision=scenario.expected_decision,
                actual_decision=result.decision.value,
                failure_type=scenario.failure_type,
                confidence=result.confidence,
                matched_rules=[r.rule for r in result.reasons],
            )
        )
        mark = "PASS" if outcomes[-1].correct else "FAIL"
        print(f"[{mark}] {scenario.scenario_id}: expected={scenario.expected_decision} actual={result.decision.value}")

    report = BenchmarkReport(outcomes=outcomes)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "BENCHMARK_RESULTS.md").write_text(report.to_markdown())

    print(f"\nAccuracy: {report.accuracy:.1%}")
    print(f"Unsafe-approval rate: {report.unsafe_approval_rate:.1%}")
    print(f"False-block rate: {report.false_block_rate:.1%}")
    print(f"Contradiction-detection accuracy: {report.contradiction_detection_accuracy:.1%}")
    print(f"\nWrote {DOCS_DIR / 'BENCHMARK_RESULTS.md'}")


if __name__ == "__main__":
    main()
