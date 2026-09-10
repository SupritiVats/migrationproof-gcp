from __future__ import annotations

import datetime
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery
from pydantic import BaseModel

from app.agents.analysis_agent import run_analysis
from app.agents.gemini_client import GeminiClient, GeminiCallError
from app.auth.dependencies import require_session
from app.models.schemas import VerificationResult
from app.storage.bigquery_client import get_bigquery_client
from app.storage.queries import fetch_project_graph_data
from app.verification.graph import DependencyGraph
from app.verification.rules import RuleContext, run_verification

router = APIRouter(prefix="/verify", tags=["verify"], dependencies=[Depends(require_session)])


class VerifyRequest(BaseModel):
    project_id: str
    target_wave: int


@router.post("", response_model=VerificationResult)
def verify(payload: VerifyRequest) -> VerificationResult:
    entities, dependencies, evidence_by_dependency, wave_of = fetch_project_graph_data(payload.project_id)
    if not entities:
        raise HTTPException(status_code=404, detail=f"No discovered entities for project '{payload.project_id}'. Run discovery first.")

    graph = DependencyGraph.build(entities, dependencies)
    ctx = RuleContext(
        graph=graph,
        wave_of=wave_of,
        evidence_by_dependency=evidence_by_dependency,
        target_wave=payload.target_wave,
    )
    result = run_verification(ctx)

    narrative = None
    try:
        narrative = run_analysis(result, client=GeminiClient())
    except GeminiCallError:
        narrative = None  # Gemini key not configured; decision/evidence still fully available without narrative.

    bq = get_bigquery_client()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result_id = str(uuid.uuid4())
    bq.insert_rows(
        "verification_results",
        [
            {
                "result_id": result_id,
                "scenario_id": payload.project_id,
                "wave_number": payload.target_wave,
                "decision": result.decision.value,
                "reasons": json.dumps([r.model_dump() for r in result.reasons]),
                "confidence": result.confidence,
                "blast_radius": json.dumps(result.blast_radius_by_entity),
                "narrative": narrative,
                "created_at": now,
            }
        ],
    )

    return VerificationResult(
        result_id=result_id,
        scenario_id=payload.project_id,
        wave_number=payload.target_wave,
        decision=result.decision,
        reasons=result.reasons,
        confidence=result.confidence,
        blast_radius=result.blast_radius_by_entity,
        narrative=narrative,
    )


@router.get("/{result_id}", response_model=None)
def get_result(result_id: str) -> dict:
    bq = get_bigquery_client()
    rows = bq.query(
        f"SELECT * FROM `{bq.table_ref('verification_results')}` WHERE result_id = @result_id LIMIT 1",
        params=[bigquery.ScalarQueryParameter("result_id", "STRING", result_id)],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Result not found")
    return rows[0]
