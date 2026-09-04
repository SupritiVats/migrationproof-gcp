"""Deterministic verification rules.

These rules are the ONLY component allowed to set the final ALLOW/BLOCK
decision. Gemini/ADK agents may only produce candidate entities, dependencies,
and evidence feeding into this module -- never the decision itself.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import Decision, Evidence, VerificationReason
from app.verification.blast_radius import compute_blast_radius
from app.verification.confidence import score_dependency_confidence
from app.verification.graph import DependencyGraph

MIN_SAFE_CONFIDENCE = 0.55
CONTRADICTION_STALENESS_HOURS = 24 * 30  # 30 days


@dataclass
class RuleContext:
    graph: DependencyGraph
    wave_of: dict[str, int]          # entity_id -> assigned wave number
    evidence_by_dependency: dict[str, list[Evidence]]
    target_wave: int                  # the wave the user is asking to verify


@dataclass
class RuleEngineResult:
    decision: Decision
    reasons: list[VerificationReason]
    confidence: float
    blast_radius_by_entity: dict[str, list[str]]


def check_cross_wave_dependency(ctx: RuleContext) -> list[VerificationReason]:
    """A dependency's target must be migrated in the same wave or earlier."""
    reasons: list[VerificationReason] = []
    entities_in_wave = [eid for eid, w in ctx.wave_of.items() if w == ctx.target_wave]

    for entity_id in entities_in_wave:
        for dep_target_id in ctx.graph.dependencies_of(entity_id):
            target_wave = ctx.wave_of.get(dep_target_id)
            if target_wave is None:
                continue  # dependency target not part of this migration plan; out of scope
            if target_wave > ctx.target_wave:
                dep = ctx.graph.find_dependency(entity_id, dep_target_id)
                reasons.append(
                    VerificationReason(
                        rule="cross_wave_dependency",
                        message=(
                            f"{entity_id} (Wave {ctx.target_wave}) depends on {dep_target_id}, "
                            f"which is scheduled for Wave {target_wave}."
                        ),
                        related_entity_ids=[entity_id, dep_target_id],
                        related_dependency_ids=[dep.dependency_id] if dep else [],
                    )
                )
    return reasons


def check_low_confidence_dependencies(ctx: RuleContext) -> list[VerificationReason]:
    """Flag dependencies whose evidence is too weak to trust for a safety decision."""
    reasons: list[VerificationReason] = []
    entities_in_wave = [eid for eid, w in ctx.wave_of.items() if w == ctx.target_wave]

    for entity_id in entities_in_wave:
        for dep_target_id in ctx.graph.dependencies_of(entity_id):
            dep = ctx.graph.find_dependency(entity_id, dep_target_id)
            if not dep:
                continue
            evidence = ctx.evidence_by_dependency.get(dep.dependency_id, [])
            confidence = score_dependency_confidence(evidence)
            if confidence < MIN_SAFE_CONFIDENCE:
                reasons.append(
                    VerificationReason(
                        rule="low_confidence_dependency",
                        message=(
                            f"Dependency {entity_id} -> {dep_target_id} has low evidence "
                            f"confidence ({confidence:.2f}); needs human review before proceeding."
                        ),
                        related_entity_ids=[entity_id, dep_target_id],
                        related_dependency_ids=[dep.dependency_id],
                    )
                )
    return reasons


def check_contradictory_evidence(ctx: RuleContext) -> list[VerificationReason]:
    """Detect when evidence for the same dependency disagrees on its existence."""
    reasons: list[VerificationReason] = []
    for dependency_id, evidence_list in ctx.evidence_by_dependency.items():
        artifact_types = {e.artifact_type for e in evidence_list}
        snippets = {e.quoted_snippet.strip().lower() for e in evidence_list}
        negation_markers = {"deprecated", "removed", "no longer", "decommissioned"}
        has_negation = any(any(marker in s for marker in negation_markers) for s in snippets)
        has_affirmation = any(not any(marker in s for marker in negation_markers) for s in snippets)
        if has_negation and has_affirmation and len(artifact_types) > 1:
            dep = ctx.graph.dependencies.get(dependency_id)
            reasons.append(
                VerificationReason(
                    rule="contradictory_evidence",
                    message=(
                        "Conflicting evidence found for this dependency: some artifacts "
                        "indicate it is active, others indicate it was removed/decommissioned."
                    ),
                    related_entity_ids=(
                        [dep.source_entity_id, dep.target_entity_id] if dep else []
                    ),
                    related_dependency_ids=[dependency_id],
                )
            )
    return reasons


RULES = [
    check_cross_wave_dependency,
    check_low_confidence_dependencies,
    check_contradictory_evidence,
]

# Rules that are severe enough to BLOCK on their own. Others are advisory
# ("needs review") but do not by themselves flip an ALLOW to a BLOCK.
BLOCKING_RULES = {"cross_wave_dependency", "contradictory_evidence"}


def run_verification(ctx: RuleContext) -> RuleEngineResult:
    all_reasons: list[VerificationReason] = []
    for rule_fn in RULES:
        all_reasons.extend(rule_fn(ctx))

    blocking_reasons = [r for r in all_reasons if r.rule in BLOCKING_RULES]
    decision = Decision.BLOCK if blocking_reasons else Decision.ALLOW

    # Overall confidence = average confidence across all dependencies touched
    # by entities in the target wave (lower confidence when reasons exist).
    entities_in_wave = [eid for eid, w in ctx.wave_of.items() if w == ctx.target_wave]
    confidences = []
    for entity_id in entities_in_wave:
        for dep_target_id in ctx.graph.dependencies_of(entity_id):
            dep = ctx.graph.find_dependency(entity_id, dep_target_id)
            if dep:
                evidence = ctx.evidence_by_dependency.get(dep.dependency_id, [])
                confidences.append(score_dependency_confidence(evidence))
    overall_confidence = sum(confidences) / len(confidences) if confidences else 1.0
    if decision == Decision.BLOCK:
        # Confidence in a BLOCK reflects confidence in the *evidence causing the block*.
        overall_confidence = max(overall_confidence, 0.9) if blocking_reasons else overall_confidence

    blast_radius_by_entity = {
        entity_id: sorted(compute_blast_radius(ctx.graph, entity_id).affected_entity_ids)
        for entity_id in entities_in_wave
    }

    return RuleEngineResult(
        decision=decision,
        reasons=all_reasons,
        confidence=round(overall_confidence, 4),
        blast_radius_by_entity=blast_radius_by_entity,
    )
