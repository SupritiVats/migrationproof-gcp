"""Discovery Agent: extracts candidate entities + dependencies from raw artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.agents.gemini_client import GeminiClient
from app.models.schemas import EntityType

PROMPT_PATH = Path(__file__).parent / "prompts" / "discovery_agent.md"


class CandidateEntity(BaseModel):
    entity_id: str
    name: str
    type: EntityType


class CandidateDependency(BaseModel):
    source_entity_id: str
    target_entity_id: str
    dependency_type: str


class DiscoveryOutput(BaseModel):
    entities: list[CandidateEntity]
    dependencies: list[CandidateDependency]


def run_discovery(artifacts: dict[str, str], scenario_id: str | None = None, client: GeminiClient | None = None) -> DiscoveryOutput:
    """`artifacts` maps filename -> raw text content."""
    client = client or GeminiClient()
    prompt_template = PROMPT_PATH.read_text()
    artifacts_blob = "\n\n".join(f"--- {name} ---\n{content}" for name, content in artifacts.items())
    prompt = prompt_template.replace("{artifacts}", artifacts_blob)

    raw: dict[str, Any] = client.generate_json(prompt, agent_name="discovery_agent", scenario_id=scenario_id)
    try:
        return DiscoveryOutput.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Discovery Agent returned a JSON shape that failed schema validation: {exc}") from exc
