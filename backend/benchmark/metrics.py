"""Benchmark metrics: compare verification engine decisions against ground truth."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScenarioOutcome:
    scenario_id: str
    expected_decision: str
    actual_decision: str
    failure_type: str
    confidence: float
    matched_rules: list[str] = field(default_factory=list)

    @property
    def correct(self) -> bool:
        return self.expected_decision == self.actual_decision

    @property
    def is_unsafe_approval(self) -> bool:
        """A migration that SHOULD have been blocked, but was allowed. The most
        dangerous class of error for a safety product."""
        return self.expected_decision == "BLOCK" and self.actual_decision == "ALLOW"

    @property
    def is_false_block(self) -> bool:
        """A safe migration that was incorrectly blocked (costly but not dangerous)."""
        return self.expected_decision == "ALLOW" and self.actual_decision == "BLOCK"


@dataclass
class BenchmarkReport:
    outcomes: list[ScenarioOutcome]

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def accuracy(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(1 for o in self.outcomes if o.correct) / self.total

    @property
    def unsafe_approval_rate(self) -> float:
        blocks_expected = [o for o in self.outcomes if o.expected_decision == "BLOCK"]
        if not blocks_expected:
            return 0.0
        return sum(1 for o in blocks_expected if o.is_unsafe_approval) / len(blocks_expected)

    @property
    def false_block_rate(self) -> float:
        allows_expected = [o for o in self.outcomes if o.expected_decision == "ALLOW"]
        if not allows_expected:
            return 0.0
        return sum(1 for o in allows_expected if o.is_false_block) / len(allows_expected)

    @property
    def contradiction_detection_accuracy(self) -> float:
        relevant = [o for o in self.outcomes if o.failure_type == "contradictory_evidence"]
        if not relevant:
            return 0.0
        return sum(1 for o in relevant if "contradictory_evidence" in o.matched_rules) / len(relevant)

    def to_markdown(self) -> str:
        lines = [
            "# MigrationProof Benchmark Results",
            "",
            "> **Note:** These results benchmark the deterministic verification engine",
            "> against hand-seeded reference data (entities/dependencies/evidence loaded",
            "> directly via `scripts/load_scenario_to_bigquery.py`), not yet the full",
            "> Gemini/ADK Discovery+Evidence extraction pipeline (Phase 4). Once a Gemini",
            "> API key is configured and the agents populate these same BigQuery tables",
            "> from raw artifacts, re-run this benchmark for true end-to-end numbers.",
            "",
            f"Scenarios evaluated: **{self.total}**",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Overall decision accuracy | {self.accuracy:.1%} |",
            f"| Unsafe-approval rate (BLOCK expected, ALLOW given) | {self.unsafe_approval_rate:.1%} |",
            f"| False-block rate (ALLOW expected, BLOCK given) | {self.false_block_rate:.1%} |",
            f"| Contradiction-detection accuracy | {self.contradiction_detection_accuracy:.1%} |",
            "",
            "## Per-scenario results",
            "",
            "| Scenario | Failure type | Expected | Actual | Confidence | Result |",
            "|---|---|---|---|---|---|",
        ]
        for o in self.outcomes:
            mark = "PASS" if o.correct else "FAIL"
            lines.append(
                f"| {o.scenario_id} | {o.failure_type} | {o.expected_decision} | "
                f"{o.actual_decision} | {o.confidence:.2f} | {mark} |"
            )
        return "\n".join(lines) + "\n"
