"""Load each scenario's reference_data.json into BigQuery.

This seeds `entities`, `dependencies`, `evidence`, `migration_waves`, and
`ground_truth` directly from the synthetic generator's hand-authored
reference data (status='verified'), so the deterministic verification engine
and the benchmark harness can be exercised end-to-end WITHOUT requiring a
Gemini API key / any LLM calls.

Once the Discovery + Evidence agents (Phase 4) are wired up with a real
Gemini key, the intent is for them to reproduce this same structured data
from the raw artifacts (vm_inventory.csv, dns_records.csv, etc.) instead of
this script -- at that point this script becomes a "ground truth seeding"
tool used only for the `ground_truth` table, not for entities/dependencies.

Usage:
    python -m scripts.load_scenario_to_bigquery [--scenario SCENARIO_ID]
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.storage.bigquery_client import get_bigquery_client  # noqa: E402

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "benchmark" / "scenarios"


def load_one(scenario_id: str) -> None:
    reference_path = SCENARIOS_DIR / scenario_id / "reference_data.json"
    reference = json.loads(reference_path.read_text())
    bq = get_bigquery_client()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    entities_rows = [{**e, "created_at": now} for e in reference["entities"]]
    dependencies_rows = [{**d, "confidence": 1.0, "created_at": now} for d in reference["dependencies"]]
    evidence_rows = [{**ev, "created_at": now} for ev in reference["evidence"]]
    wave_rows = reference["migration_waves"]
    ground_truth_rows = reference["ground_truth"]

    for table, rows in [
        ("entities", entities_rows),
        ("dependencies", dependencies_rows),
        ("evidence", evidence_rows),
        ("migration_waves", wave_rows),
        ("ground_truth", ground_truth_rows),
    ]:
        errors = bq.insert_rows(table, rows)
        status = "OK" if not errors else f"ERRORS: {errors}"
        print(f"  {table}: inserted {len(rows)} rows [{status}]")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default=None, help="Load a single scenario_id; default: all")
    args = parser.parse_args()

    scenario_ids = (
        [args.scenario] if args.scenario else sorted(p.name for p in SCENARIOS_DIR.iterdir() if p.is_dir())
    )
    for scenario_id in scenario_ids:
        print(f"Loading {scenario_id}...")
        load_one(scenario_id)

    print(f"\nLoaded {len(scenario_ids)} scenario(s) into BigQuery.")


if __name__ == "__main__":
    main()
