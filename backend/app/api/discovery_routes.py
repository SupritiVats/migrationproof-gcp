from fastapi import APIRouter, Depends, HTTPException

from app.agents.gemini_client import GeminiCallError
from app.agents.orchestrator import run_discovery_pipeline
from app.auth.dependencies import require_session

router = APIRouter(prefix="/discovery", tags=["discovery"], dependencies=[Depends(require_session)])


@router.post("/run/{project_id}")
def run_discovery_endpoint(project_id: str) -> dict:
    try:
        return run_discovery_pipeline(project_id)
    except (ValueError, GeminiCallError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
