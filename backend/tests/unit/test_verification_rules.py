from app.models.schemas import Decision, Dependency, DependencyStatus, Entity, EntityType, Evidence
from app.verification.graph import DependencyGraph
from app.verification.rules import RuleContext, run_verification


def make_entity(entity_id: str, entity_type: EntityType = EntityType.SERVICE) -> Entity:
    return Entity(entity_id=entity_id, name=entity_id, type=entity_type)


def make_dependency(dep_id: str, source: str, target: str) -> Dependency:
    return Dependency(
        dependency_id=dep_id,
        source_entity_id=source,
        target_entity_id=target,
        dependency_type="reads_writes",
        status=DependencyStatus.VERIFIED,
    )


def make_evidence(evidence_id: str, dependency_id: str, artifact_type: str, snippet: str) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        dependency_id=dependency_id,
        artifact_uri=f"gs://bucket/{artifact_type}.txt",
        artifact_type=artifact_type,
        quoted_snippet=snippet,
        extracted_by="evidence_agent",
    )


def test_cross_wave_dependency_blocks():
    entities = [make_entity("checkout-api"), make_entity("mysql-prod", EntityType.DATABASE)]
    deps = [make_dependency("d1", "checkout-api", "mysql-prod")]
    graph = DependencyGraph.build(entities, deps)

    evidence = {
        "d1": [
            make_evidence("e1", "d1", "application_config", "DB_HOST=mysql-prod.internal"),
            make_evidence("e2", "d1", "dns_record", "mysql-prod.internal -> 10.20.0.14"),
        ]
    }
    ctx = RuleContext(
        graph=graph,
        wave_of={"checkout-api": 1, "mysql-prod": 3},
        evidence_by_dependency=evidence,
        target_wave=1,
    )
    result = run_verification(ctx)
    assert result.decision == Decision.BLOCK
    assert any(r.rule == "cross_wave_dependency" for r in result.reasons)


def test_safe_same_wave_migration_allows():
    entities = [make_entity("frontend"), make_entity("checkout-api")]
    deps = [make_dependency("d1", "frontend", "checkout-api")]
    graph = DependencyGraph.build(entities, deps)

    evidence = {
        "d1": [
            make_evidence("e1", "d1", "application_config", "API_URL=http://checkout-api"),
            make_evidence("e2", "d1", "network_connection", "frontend -> checkout-api:443"),
        ]
    }
    ctx = RuleContext(
        graph=graph,
        wave_of={"frontend": 1, "checkout-api": 1},
        evidence_by_dependency=evidence,
        target_wave=1,
    )
    result = run_verification(ctx)
    assert result.decision == Decision.ALLOW
    assert not any(r.rule == "cross_wave_dependency" for r in result.reasons)


def test_low_confidence_dependency_is_advisory_not_blocking():
    entities = [make_entity("service-a"), make_entity("service-b")]
    deps = [make_dependency("d1", "service-a", "service-b")]
    graph = DependencyGraph.build(entities, deps)

    evidence = {"d1": [make_evidence("e1", "d1", "service_catalog", "possibly related")]}
    ctx = RuleContext(
        graph=graph,
        wave_of={"service-a": 1, "service-b": 1},
        evidence_by_dependency=evidence,
        target_wave=1,
    )
    result = run_verification(ctx)
    assert any(r.rule == "low_confidence_dependency" for r in result.reasons)
    # Low confidence alone should not flip an otherwise-safe same-wave migration to BLOCK.
    assert result.decision == Decision.ALLOW


def test_contradictory_evidence_blocks():
    entities = [make_entity("order-service"), make_entity("legacy-queue")]
    deps = [make_dependency("d1", "order-service", "legacy-queue")]
    graph = DependencyGraph.build(entities, deps)

    evidence = {
        "d1": [
            make_evidence("e1", "d1", "application_config", "QUEUE_HOST=legacy-queue.internal"),
            make_evidence("e2", "d1", "architecture_doc", "legacy-queue was decommissioned last quarter"),
        ]
    }
    ctx = RuleContext(
        graph=graph,
        wave_of={"order-service": 1, "legacy-queue": 1},
        evidence_by_dependency=evidence,
        target_wave=1,
    )
    result = run_verification(ctx)
    assert result.decision == Decision.BLOCK
    assert any(r.rule == "contradictory_evidence" for r in result.reasons)


def test_blast_radius_includes_transitive_dependents():
    entities = [make_entity(x) for x in ["frontend", "checkout-api", "order-service", "mysql-prod"]]
    deps = [
        make_dependency("d1", "checkout-api", "mysql-prod"),
        make_dependency("d2", "order-service", "checkout-api"),
        make_dependency("d3", "frontend", "order-service"),
    ]
    graph = DependencyGraph.build(entities, deps)
    evidence = {
        d.dependency_id: [make_evidence(f"e{d.dependency_id}", d.dependency_id, "application_config", "ref")]
        for d in deps
    }
    ctx = RuleContext(
        graph=graph,
        wave_of={"frontend": 1, "checkout-api": 1, "order-service": 1, "mysql-prod": 3},
        evidence_by_dependency=evidence,
        target_wave=1,
    )
    result = run_verification(ctx)
    assert result.decision == Decision.BLOCK
    affected = set(result.blast_radius_by_entity.get("mysql-prod", []))
    # mysql-prod isn't in target_wave, so blast radius is keyed by wave-1 entities instead;
    # check checkout-api's blast radius covers its dependents.
    assert set(result.blast_radius_by_entity["checkout-api"]) >= {"order-service", "frontend"}
