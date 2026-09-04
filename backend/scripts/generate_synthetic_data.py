"""Generate the synthetic RetailCo environment + 8 benchmark scenarios.

For each scenario this writes:
  - raw artifacts (vm_inventory.csv, dns_records.csv, network_connections.csv,
    application_config.json, architecture.md, service_catalog.csv, migration_plan.json)
    to backend/benchmark/scenarios/<scenario_id>/ AND uploads them to the
    GCS synthetic-data bucket.
  - a reference_data.json containing the "known good" structured entities/
    dependencies/evidence for that scenario. This is what the Discovery +
    Evidence agents (Phase 4) are expected to (re)produce from the raw
    artifacts. Until Gemini is wired up, `load_scenario_to_bigquery.py` can
    load this reference data directly so the verification engine and
    benchmark can be exercised end-to-end without any LLM calls/cost.

Usage:
    python -m scripts.generate_synthetic_data [--upload]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.scenario_definitions import (  # noqa: E402
    BASELINE_DEPENDENCIES,
    BASELINE_ENTITIES,
    SCENARIOS,
    STRONG_EVIDENCE,
    Scenario,
)

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "benchmark" / "scenarios"


def _dep_key(source: str, target: str) -> str:
    return f"{source}->{target}"


def build_reference_data(scenario: Scenario) -> dict:
    entities = [dict(e, scenario_id=scenario.scenario_id) for e in BASELINE_ENTITIES]

    dependencies = []
    evidence = []
    all_deps = list(BASELINE_DEPENDENCIES) + [
        (s, t, dt) for (s, t, dt) in scenario.extra_dependencies
    ]

    for source, target, dep_type in all_deps:
        dep_id = f"{scenario.scenario_id}::dep::{source}->{target}"
        dependencies.append(
            {
                "dependency_id": dep_id,
                "source_entity_id": source,
                "target_entity_id": target,
                "dependency_type": dep_type,
                "status": "verified",
                "scenario_id": scenario.scenario_id,
            }
        )

        key = _dep_key(source, target)
        override = scenario.evidence_overrides.get(key)
        if override:
            snippets = override
        else:
            snippets = [
                ("application_config", f"{source.upper().replace('-', '_')}_TARGET={target}.internal"),
                ("network_connection", f"{source} -> {target}:443 observed in flow logs"),
            ]
        for i, (artifact_type, snippet) in enumerate(snippets):
            evidence.append(
                {
                    "evidence_id": f"{dep_id}::ev{i}",
                    "dependency_id": dep_id,
                    "artifact_uri": f"gs://SYNTHETIC_BUCKET/{scenario.scenario_id}/{artifact_type}.txt",
                    "artifact_type": artifact_type,
                    "quoted_snippet": snippet,
                    "extracted_by": "synthetic_generator",
                }
            )

    migration_waves = [
        {"wave_id": f"{scenario.scenario_id}::wave::{eid}", "wave_number": wave, "entity_id": eid, "scenario_id": scenario.scenario_id}
        for eid, wave in scenario.wave_of.items()
    ]

    ground_truth_rows = []
    for source, target, _ in all_deps:
        ground_truth_rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "entity_id_a": source,
                "entity_id_b": target,
                "is_dependency": True,
                "expected_wave_conflict": scenario.failure_type == "cross_wave_dependency",
                "failure_type": scenario.failure_type,
                "expected_decision": scenario.expected_decision,
            }
        )

    return {
        "scenario_id": scenario.scenario_id,
        "description": scenario.description,
        "target_wave": scenario.target_wave,
        "expected_decision": scenario.expected_decision,
        "failure_type": scenario.failure_type,
        "entities": entities,
        "dependencies": dependencies,
        "evidence": evidence,
        "migration_waves": migration_waves,
        "ground_truth": ground_truth_rows,
    }


def render_vm_inventory_csv(scenario: Scenario) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["vm_name", "entity_id", "wave", "status"])
    for eid, wave in scenario.wave_of.items():
        writer.writerow([f"vm-{eid}", eid, wave, "running"])
    return buf.getvalue()


def render_service_catalog_csv(scenario: Scenario) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["entity_id", "type", "owner_team"])
    for e in BASELINE_ENTITIES:
        writer.writerow([e["entity_id"], e["type"], "platform-eng"])
    return buf.getvalue()


def render_dns_records_csv(scenario: Scenario) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["record", "target", "note"])
    writer.writerow(["checkout.retailco.com", "load-balancer.internal", "active"])
    if scenario.scenario_id == "scn-03-stale-dns-reference":
        writer.writerow(["mysql-prod.internal", "10.20.0.14", "DECOMMISSIONED - do not use"])
    else:
        writer.writerow(["mysql-prod.internal", "10.20.0.14", "active"])
    return buf.getvalue()


def render_application_config_json(scenario: Scenario, reference: dict) -> str:
    config: dict[str, str] = {}
    for dep in reference["dependencies"]:
        key = f"{dep['source_entity_id'].upper().replace('-', '_')}_TARGET"
        config[key] = f"{dep['target_entity_id']}.internal"
    return json.dumps(config, indent=2)


def render_architecture_md(scenario: Scenario) -> str:
    lines = [f"# RetailCo Architecture — {scenario.scenario_id}", "", scenario.description, "", "## Services"]
    for e in BASELINE_ENTITIES:
        lines.append(f"- **{e['name']}** ({e['type']})")
    lines.append("")
    lines.append("## Notes")
    for key, snippets in scenario.evidence_overrides.items():
        for artifact_type, snippet in snippets:
            if artifact_type == "architecture_doc":
                lines.append(f"- {key}: {snippet}")
    return "\n".join(lines)


def render_migration_plan_json(scenario: Scenario) -> str:
    return json.dumps(
        {
            "scenario_id": scenario.scenario_id,
            "target_wave": scenario.target_wave,
            "waves": scenario.wave_of,
        },
        indent=2,
    )


def write_scenario_files(scenario: Scenario, reference: dict) -> Path:
    out_dir = SCENARIOS_DIR / scenario.scenario_id
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "vm_inventory.csv").write_text(render_vm_inventory_csv(scenario))
    (out_dir / "service_catalog.csv").write_text(render_service_catalog_csv(scenario))
    (out_dir / "dns_records.csv").write_text(render_dns_records_csv(scenario))
    (out_dir / "application_config.json").write_text(render_application_config_json(scenario, reference))
    (out_dir / "architecture.md").write_text(render_architecture_md(scenario))
    (out_dir / "migration_plan.json").write_text(render_migration_plan_json(scenario))
    (out_dir / "reference_data.json").write_text(json.dumps(reference, indent=2))
    return out_dir


def maybe_upload(scenario_id: str, out_dir: Path) -> None:
    from app.storage.gcs_client import get_gcs_client

    client = get_gcs_client()
    for file_path in out_dir.iterdir():
        if file_path.name == "reference_data.json":
            continue  # internal only, not a "raw artifact" the agents would see
        uri = client.upload_synthetic(scenario_id, file_path.name, file_path.read_bytes())
        print(f"  uploaded {uri}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true", help="Also upload artifacts to GCS")
    args = parser.parse_args()

    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    for scenario in SCENARIOS:
        reference = build_reference_data(scenario)
        out_dir = write_scenario_files(scenario, reference)
        print(f"generated {scenario.scenario_id} -> {out_dir}")
        if args.upload:
            maybe_upload(scenario.scenario_id, out_dir)

    print(f"\nGenerated {len(SCENARIOS)} scenarios under {SCENARIOS_DIR}")


if __name__ == "__main__":
    main()
