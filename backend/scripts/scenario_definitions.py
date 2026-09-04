"""Definitions for the synthetic RetailCo environment and its benchmark scenarios.

Each scenario reuses the same baseline RetailCo entities/dependencies, but varies:
  - the proposed migration plan (which wave each entity is assigned to)
  - which artifacts/evidence are seeded (including deliberately broken ones)
  - the expected ("ground truth") ALLOW/BLOCK decision for the wave being verified

This is the foundation for the benchmark (Phase 7): running the pipeline against
every scenario and comparing its decision to `expected_decision` here.
"""
from dataclasses import dataclass, field

# --- Baseline RetailCo entities -------------------------------------------------
# type must match app.models.schemas.EntityType
BASELINE_ENTITIES = [
    {"entity_id": "frontend", "name": "frontend", "type": "service"},
    {"entity_id": "load-balancer", "name": "load-balancer", "type": "service"},
    {"entity_id": "checkout-api", "name": "checkout-api", "type": "service"},
    {"entity_id": "order-service", "name": "order-service", "type": "service"},
    {"entity_id": "payment-service", "name": "payment-service", "type": "service"},
    {"entity_id": "mysql-prod", "name": "mysql-prod", "type": "database"},
    {"entity_id": "redis", "name": "redis", "type": "database"},
    {"entity_id": "kafka", "name": "kafka", "type": "service"},
    {"entity_id": "monitoring", "name": "monitoring", "type": "service"},
    {"entity_id": "external-payment-api", "name": "external-payment-api", "type": "external_api"},
]

# --- Baseline verified dependencies (source depends on target) -----------------
BASELINE_DEPENDENCIES = [
    ("load-balancer", "frontend", "routes_to"),
    ("frontend", "checkout-api", "calls_api"),
    ("checkout-api", "mysql-prod", "reads_writes"),
    ("checkout-api", "redis", "reads_writes"),
    ("checkout-api", "payment-service", "calls_api"),
    ("order-service", "checkout-api", "calls_api"),
    ("order-service", "kafka", "publishes_to"),
    ("payment-service", "external-payment-api", "calls_api"),
]

STRONG_EVIDENCE = [
    ("application_config", "{key}={value}"),
    ("network_connection", "{source} -> {target}:443 observed in flow logs"),
]


@dataclass
class Scenario:
    scenario_id: str
    description: str
    wave_of: dict[str, int]                     # entity_id -> wave number
    target_wave: int                             # which wave the user is verifying
    expected_decision: str                       # ALLOW | BLOCK
    failure_type: str                            # none | cross_wave_dependency | ...
    extra_dependencies: list[tuple[str, str, str]] = field(default_factory=list)
    evidence_overrides: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    # evidence_overrides: dependency key "source->target" -> [(artifact_type, snippet), ...]
    # If present, REPLACES the default strong evidence for that dependency.
    notes: str = ""


DEFAULT_WAVE_OF = {
    "load-balancer": 1,
    "frontend": 1,
    "checkout-api": 1,
    "order-service": 1,
    "payment-service": 1,
    "mysql-prod": 1,
    "redis": 1,
    "kafka": 1,
    "monitoring": 2,
    "external-payment-api": 1,  # external, not actually migrated, but present in plan for completeness
}

SCENARIOS: list[Scenario] = [
    Scenario(
        scenario_id="scn-01-safe-migration",
        description="All dependencies co-scheduled correctly. Should be ALLOWed.",
        wave_of=dict(DEFAULT_WAVE_OF),
        target_wave=1,
        expected_decision="ALLOW",
        failure_type="none",
    ),
    Scenario(
        scenario_id="scn-02-db-migrated-after-app",
        description="checkout-api (Wave 1) depends on mysql-prod, but mysql-prod is scheduled for Wave 3.",
        wave_of={**DEFAULT_WAVE_OF, "mysql-prod": 3},
        target_wave=1,
        expected_decision="BLOCK",
        failure_type="cross_wave_dependency",
    ),
    Scenario(
        scenario_id="scn-03-stale-dns-reference",
        description="DNS record for mysql-prod was marked decommissioned, but application config still references it.",
        wave_of=dict(DEFAULT_WAVE_OF),
        target_wave=1,
        expected_decision="BLOCK",
        failure_type="contradictory_evidence",
        evidence_overrides={
            "checkout-api->mysql-prod": [
                ("application_config", "DB_HOST=mysql-prod.internal"),
                ("dns_record", "mysql-prod.internal marked decommissioned; DNS record removed last migration cycle"),
            ]
        },
    ),
    Scenario(
        scenario_id="scn-04-hidden-dependency-in-config",
        description="A dependency (order-service -> kafka) is only visible in one weak artifact (service catalog note).",
        wave_of=dict(DEFAULT_WAVE_OF),
        target_wave=1,
        expected_decision="ALLOW",
        failure_type="low_confidence_dependency",
        evidence_overrides={
            "order-service->kafka": [
                ("service_catalog", "order-service possibly related to kafka messaging tier"),
            ]
        },
        notes="Should surface as an advisory low-confidence flag for human review, but not auto-block.",
    ),
    Scenario(
        scenario_id="scn-05-forgotten-external-dependency",
        description="payment-service depends on an external payment API outside migration scope.",
        wave_of={k: v for k, v in DEFAULT_WAVE_OF.items() if k != "external-payment-api"},
        target_wave=1,
        expected_decision="ALLOW",
        failure_type="none",
        notes="External dependency is out of the migration plan's scope; not a blocking condition by itself.",
    ),
    Scenario(
        scenario_id="scn-06-incompatible-waves-two-services",
        description="order-service (Wave 1) depends on checkout-api, but checkout-api is pushed to Wave 2.",
        wave_of={**DEFAULT_WAVE_OF, "checkout-api": 2},
        target_wave=1,
        expected_decision="BLOCK",
        failure_type="cross_wave_dependency",
    ),
    Scenario(
        scenario_id="scn-07-stale-inventory-no-impact",
        description="VM inventory timestamp is old, but no dependency evidence conflicts. Should still ALLOW.",
        wave_of=dict(DEFAULT_WAVE_OF),
        target_wave=1,
        expected_decision="ALLOW",
        failure_type="none",
        notes="Simulates stale but non-contradictory inventory metadata.",
    ),
    Scenario(
        scenario_id="scn-08-contradictory-evidence-queue",
        description="order-service->kafka: config says active, architecture doc says kafka was decommissioned.",
        wave_of=dict(DEFAULT_WAVE_OF),
        target_wave=1,
        expected_decision="BLOCK",
        failure_type="contradictory_evidence",
        evidence_overrides={
            "order-service->kafka": [
                ("application_config", "KAFKA_BROKER=kafka.internal:9092"),
                ("architecture_doc", "kafka message broker was decommissioned and replaced by pubsub"),
            ]
        },
    ),
]
