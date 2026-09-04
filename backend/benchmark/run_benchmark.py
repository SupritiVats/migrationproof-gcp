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

from app.storage.bigquery_client import get_bigquery_client  # noqa: E402
from app.storage.queries import fetch_project_graph_data  # noqa: E402
from app.verification.rules import RuleContext, run_verification  # noqa: E402
from benchmark.metrics import BenchmarkReport, ScenarioOutcome  # noqa: E402
from scripts.scenario_definitions import SCENARIOS  # noqa: E402

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"


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
        entities, dependencies, evidence_by_dependency, wave_of = fetch_project_graph_data(scenario.scenario_id)
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
