"""Dependency graph model built from verified entities/dependencies."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from app.models.schemas import Dependency, DependencyStatus, Entity


@dataclass
class DependencyGraph:
    entities: dict[str, Entity] = field(default_factory=dict)
    dependencies: dict[str, Dependency] = field(default_factory=dict)
    # adjacency: source depends on target -> edges[source] = [target, ...]
    edges: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    reverse_edges: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    def build(cls, entities: list[Entity], dependencies: list[Dependency]) -> "DependencyGraph":
        graph = cls()
        for e in entities:
            graph.entities[e.entity_id] = e
        for d in dependencies:
            if d.status != DependencyStatus.VERIFIED:
                continue
            graph.dependencies[d.dependency_id] = d
            graph.edges[d.source_entity_id].append(d.target_entity_id)
            graph.reverse_edges[d.target_entity_id].append(d.source_entity_id)
        return graph

    def dependencies_of(self, entity_id: str) -> list[str]:
        """Entities that `entity_id` directly depends on."""
        return list(self.edges.get(entity_id, []))

    def dependents_of(self, entity_id: str) -> list[str]:
        """Entities that directly depend on `entity_id`."""
        return list(self.reverse_edges.get(entity_id, []))

    def downstream_closure(self, entity_id: str) -> set[str]:
        """All entities transitively depending on `entity_id` (used for blast radius)."""
        visited: set[str] = set()
        queue = deque(self.dependents_of(entity_id))
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.dependents_of(current))
        return visited

    def find_dependency(self, source_id: str, target_id: str) -> Dependency | None:
        for dep in self.dependencies.values():
            if dep.source_entity_id == source_id and dep.target_entity_id == target_id:
                return dep
        return None
