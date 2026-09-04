"""Blast-radius computation: what breaks downstream if an entity is disrupted."""
from app.models.schemas import BlastRadius
from app.verification.graph import DependencyGraph


def compute_blast_radius(graph: DependencyGraph, entity_id: str) -> BlastRadius:
    """All entities that transitively depend on `entity_id`.

    If `entity_id` (e.g. a database) is migrated/disrupted unsafely, everything
    in this set is a candidate for user-facing impact.
    """
    affected = graph.downstream_closure(entity_id)
    return BlastRadius(root_entity_id=entity_id, affected_entity_ids=sorted(affected))
