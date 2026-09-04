"""Thin wrapper around google-generativeai enforcing JSON-only output, with
retry-on-invalid-JSON and call logging to BigQuery (llm_call_log) for cost
tracking / auditability.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

import google.generativeai as genai

from app.config import get_settings


class GeminiCallError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise GeminiCallError(
                "GEMINI_API_KEY is not set. Add it to .env (local) or Secret Manager (prod) "
                "before running any agent that calls Gemini."
            )
        genai.configure(api_key=settings.gemini_api_key)
        self.model_name = settings.gemini_model
        self.model = genai.GenerativeModel(self.model_name)

    def generate_json(self, prompt: str, agent_name: str, scenario_id: str | None = None, max_retries: int = 2) -> dict[str, Any]:
        """Call Gemini expecting a strict JSON object response. Retries once on
        invalid JSON by re-prompting with the parse error appended."""
        last_error: Exception | None = None
        attempt_prompt = prompt

        for attempt in range(max_retries + 1):
            start = time.monotonic()
            success = False
            error_message = None
            usage = None
            try:
                response = self.model.generate_content(
                    attempt_prompt,
                    generation_config=genai.types.GenerationConfig(response_mime_type="application/json"),
                )
                text = response.text
                usage = getattr(response, "usage_metadata", None)
                parsed = json.loads(text)
                success = True
                return parsed
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                error_message = str(exc)
                attempt_prompt = (
                    f"{prompt}\n\nYour previous response was not valid JSON ({exc}). "
                    "Return ONLY valid JSON matching the schema, nothing else."
                )
            finally:
                self._log_call(
                    agent_name=agent_name,
                    scenario_id=scenario_id,
                    latency_ms=int((time.monotonic() - start) * 1000),
                    success=success,
                    error_message=error_message,
                    usage=usage,
                )

        raise GeminiCallError(f"Gemini did not return valid JSON after {max_retries + 1} attempts: {last_error}")

    def _log_call(self, agent_name: str, scenario_id: str | None, latency_ms: int, success: bool, error_message: str | None, usage) -> None:
        try:
            from app.storage.bigquery_client import get_bigquery_client
            import datetime

            bq = get_bigquery_client()
            bq.insert_rows(
                "llm_call_log",
                [
                    {
                        "call_id": str(uuid.uuid4()),
                        "agent": agent_name,
                        "model": self.model_name,
                        "scenario_id": scenario_id,
                        "prompt_tokens": getattr(usage, "prompt_token_count", None) if usage else None,
                        "completion_tokens": getattr(usage, "candidates_token_count", None) if usage else None,
                        "latency_ms": latency_ms,
                        "success": success,
                        "error_message": error_message,
                        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                ],
            )
        except Exception:
            # Logging must never break the agent pipeline.
            pass
