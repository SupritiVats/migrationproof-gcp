"""Confidence scoring for a dependency claim, based on its supporting evidence."""
from app.models.schemas import Evidence

# Weight per distinct evidence artifact type. More independent, higher-trust
# sources -> higher confidence. Tuned for the synthetic artifact types used
# in this project; revisit if new artifact types are introduced.
ARTIFACT_TYPE_WEIGHTS: dict[str, float] = {
    "application_config": 0.45,
    "dns_record": 0.35,
    "network_connection": 0.30,
    "architecture_doc": 0.25,
    "vm_inventory": 0.20,
    "service_catalog": 0.15,
}
DEFAULT_WEIGHT = 0.10


def score_dependency_confidence(evidence: list[Evidence]) -> float:
    """Combine independent evidence sources into a single 0..1 confidence score.

    Uses a "noisy-OR" style combination so that multiple independent, weaker
    sources can still add up to high confidence, while a single source caps
    out below 1.0 (never fully certain from one artifact alone).
    """
    if not evidence:
        return 0.0

    distinct_types = {e.artifact_type for e in evidence}
    probability_none_supports = 1.0
    for artifact_type in distinct_types:
        weight = ARTIFACT_TYPE_WEIGHTS.get(artifact_type, DEFAULT_WEIGHT)
        probability_none_supports *= (1.0 - weight)

    confidence = 1.0 - probability_none_supports
    return round(min(confidence, 0.99), 4)
