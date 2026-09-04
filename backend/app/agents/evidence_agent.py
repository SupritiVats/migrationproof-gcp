"""Evidence Agent: finds supporting/contradicting artifact excerpts for each
candidate dependency. Any dependency with zero evidence is dropped by the
caller before it ever reaches the verification engine (see orchestrator.py).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.agents.discovery_agent import CandidateDependency
from app.agents.gemini_client import GeminiClient

PROMPT_PATH = Path(__file__).parent / "prompts" / "evidence_agent.md"

VALID_ARTIFACT_TYPES = {
    "application_config",
    "dns_record",
    "network_connection",
    "architecture_doc",
    "vm_inventory",
    "service_catalog",
}


class EvidenceItem(BaseModel):
    artifact_type: str
    quoted_snippet: str


class DependencyEvidence(BaseModel):
    source_entity_id: str
    target_entity_id: str
    evidence: list[EvidenceItem]


class EvidenceOutput(BaseModel):
    dependency_evidence: list[DependencyEvidence]


def run_evidence(
    candidate_dependencies: list[CandidateDependency],
    artifacts: dict[str, str],
    scenario_id: str | None = None,
    client: GeminiClient | None = None,
) -> EvidenceOutput:
    client = client or GeminiClient()
    prompt_template = PROMPT_PATH.read_text()
    artifacts_blob = "\n\n".join(f"--- {name} ---\n{content}" for name, content in artifacts.items())
    candidates_blob = json.dumps([c.model_dump() for c in candidate_dependencies], indent=2)
    prompt = prompt_template.replace("{candidate_dependencies}", candidates_blob).replace("{artifacts}", artifacts_blob)

    raw: dict[str, Any] = client.generate_json(prompt, agent_name="evidence_agent", scenario_id=scenario_id)
    try:
        output = EvidenceOutput.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Evidence Agent returned a JSON shape that failed schema validation: {exc}") from exc

    # Defense in depth: drop any evidence with an artifact_type outside our known set
    # or an empty snippet, rather than trusting the model blindly.
    for dep_evidence in output.dependency_evidence:
        dep_evidence.evidence = [
            e for e in dep_evidence.evidence if e.artifact_type in VALID_ARTIFACT_TYPES and e.quoted_snippet.strip()
        ]
    output.dependency_evidence = [d for d in output.dependency_evidence if d.evidence]
    return output
