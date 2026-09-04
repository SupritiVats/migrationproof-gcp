"""Thin wrapper around the google-genai SDK.

Supports two backends via the `GEMINI_BACKEND` env var:
- "vertexai" (default): Gemini via Vertex AI, authenticated with the project's
  service account and billed to the GCP project (works with the $300 trial).
- "api_key": Generative Language API with a GEMINI_API_KEY from AI Studio.

Enforces JSON-only output for agent calls, retries once on invalid JSON, and
logs every call to BigQuery (llm_call_log) for cost tracking / auditability.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.config import get_settings


class GeminiCallError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.model_name = settings.gemini_model
        if settings.gemini_backend == "api_key":
            if not settings.gemini_api_key:
                raise GeminiCallError(
                    "GEMINI_API_KEY is not set. Add it to .env (local) or Secret Manager (prod), "
                    "or set GEMINI_BACKEND=vertexai to use the project's service account instead."
                )
            self.client = genai.Client(api_key=settings.gemini_api_key)
        else:  # vertexai
            self.client = genai.Client(
                vertexai=True,
                project=settings.gcp_project_id,
                location=settings.gcp_region,
            )

    def generate_json(self, prompt: str, agent_name: str, scenario_id: str | None = None, max_retries: int = 2) -> dict[str, Any]:
        """Call Gemini expecting a strict JSON object response. Retries on
        invalid JSON by re-prompting with the parse error appended."""
        last_error: Exception | None = None
        attempt_prompt = prompt

        for _ in range(max_retries + 1):
            start = time.monotonic()
            success = False
            error_message = None
            usage = None
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=attempt_prompt,
                    config=genai_types.GenerateContentConfig(response_mime_type="application/json"),
                )
                usage = getattr(response, "usage_metadata", None)
                parsed = json.loads(response.text)
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

    def generate_text(self, prompt: str, agent_name: str, scenario_id: str | None = None) -> str:
        """Plain-text generation (Analysis agent narrative)."""
        start = time.monotonic()
        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            usage = getattr(response, "usage_metadata", None)
            self._log_call(
                agent_name=agent_name, scenario_id=scenario_id,
                latency_ms=int((time.monotonic() - start) * 1000),
                success=True, error_message=None, usage=usage,
            )
            return response.text.strip()
        except Exception as exc:
            self._log_call(
                agent_name=agent_name, scenario_id=scenario_id,
                latency_ms=int((time.monotonic() - start) * 1000),
                success=False, error_message=str(exc), usage=None,
            )
            raise GeminiCallError(str(exc)) from exc

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
