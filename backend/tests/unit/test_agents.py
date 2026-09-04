"""Unit tests for Discovery + Evidence agents using a mocked Gemini client
(no network calls, no API key required)."""
from unittest.mock import MagicMock

import pytest

from app.agents.discovery_agent import CandidateDependency, run_discovery
from app.agents.evidence_agent import run_evidence


def make_mock_client(json_response: dict) -> MagicMock:
    client = MagicMock()
    client.generate_json.return_value = json_response
    return client


def test_discovery_agent_parses_valid_response():
    mock_client = make_mock_client(
        {
            "entities": [
                {"entity_id": "checkout-api", "name": "checkout-api", "type": "service"},
                {"entity_id": "mysql-prod", "name": "mysql-prod", "type": "database"},
            ],
            "dependencies": [
                {"source_entity_id": "checkout-api", "target_entity_id": "mysql-prod", "dependency_type": "reads_writes"}
            ],
        }
    )
    result = run_discovery({"config.json": "DB_HOST=mysql-prod"}, client=mock_client)
    assert len(result.entities) == 2
    assert result.dependencies[0].source_entity_id == "checkout-api"


def test_discovery_agent_rejects_invalid_schema():
    mock_client = make_mock_client({"entities": [{"entity_id": "x"}], "dependencies": []})  # missing required fields
    with pytest.raises(ValueError):
        run_discovery({"a.txt": "irrelevant"}, client=mock_client)


def test_evidence_agent_drops_dependencies_with_no_evidence():
    mock_client = make_mock_client(
        {
            "dependency_evidence": [
                {
                    "source_entity_id": "checkout-api",
                    "target_entity_id": "mysql-prod",
                    "evidence": [{"artifact_type": "application_config", "quoted_snippet": "DB_HOST=mysql-prod"}],
                },
                {
                    "source_entity_id": "checkout-api",
                    "target_entity_id": "ghost-service",
                    "evidence": [],  # no evidence -> must be dropped
                },
            ]
        }
    )
    candidates = [
        CandidateDependency(source_entity_id="checkout-api", target_entity_id="mysql-prod", dependency_type="reads_writes"),
        CandidateDependency(source_entity_id="checkout-api", target_entity_id="ghost-service", dependency_type="calls_api"),
    ]
    result = run_evidence(candidates, {"config.json": "DB_HOST=mysql-prod"}, client=mock_client)
    assert len(result.dependency_evidence) == 1
    assert result.dependency_evidence[0].target_entity_id == "mysql-prod"


def test_evidence_agent_filters_unknown_artifact_types():
    mock_client = make_mock_client(
        {
            "dependency_evidence": [
                {
                    "source_entity_id": "a",
                    "target_entity_id": "b",
                    "evidence": [
                        {"artifact_type": "application_config", "quoted_snippet": "valid"},
                        {"artifact_type": "made_up_type", "quoted_snippet": "should be filtered"},
                    ],
                }
            ]
        }
    )
    result = run_evidence(
        [CandidateDependency(source_entity_id="a", target_entity_id="b", dependency_type="calls_api")],
        {"x.txt": "irrelevant"},
        client=mock_client,
    )
    assert len(result.dependency_evidence[0].evidence) == 1
    assert result.dependency_evidence[0].evidence[0].artifact_type == "application_config"
