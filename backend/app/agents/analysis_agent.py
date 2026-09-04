"""Analysis Agent: produces a human-readable narrative for an ALREADY-DECIDED
verification result. This agent structurally cannot alter the decision --
it only receives decision/confidence/reasons/blast_radius as read-only
context and returns plain text.
"""
from __future__ import annotations

from pathlib import Path

from app.agents.gemini_client import GeminiClient
from app.verification.rules import RuleEngineResult

PROMPT_PATH = Path(__file__).parent / "prompts" / "analysis_agent.md"


def run_analysis(result: RuleEngineResult, client: GeminiClient | None = None) -> str:
    client = client or GeminiClient()
    prompt_template = PROMPT_PATH.read_text()
    reasons_text = "\n".join(f"- [{r.rule}] {r.message}" for r in result.reasons) or "None"
    blast_radius_text = (
        "\n".join(f"- {entity}: {', '.join(affected) or 'none'}" for entity, affected in result.blast_radius_by_entity.items())
        or "None"
    )
    prompt = (
        prompt_template.replace("{decision}", result.decision.value)
        .replace("{confidence}", f"{result.confidence:.2f}")
        .replace("{reasons}", reasons_text)
        .replace("{blast_radius}", blast_radius_text)
    )
    # Analysis agent returns plain text, not JSON -- use the raw model directly.
    import time

    start = time.monotonic()
    response = client.model.generate_content(prompt)
    client._log_call(
        agent_name="analysis_agent",
        scenario_id=None,
        latency_ms=int((time.monotonic() - start) * 1000),
        success=True,
        error_message=None,
        usage=getattr(response, "usage_metadata", None),
    )
    return response.text.strip()
