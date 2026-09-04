from fastapi import APIRouter, Depends
from google.cloud import bigquery

from app.auth.dependencies import require_session
from app.storage.bigquery_client import get_bigquery_client

router = APIRouter(tags=["inspection"], dependencies=[Depends(require_session)])


def _project_param(project_id: str) -> bigquery.ScalarQueryParameter:
    return bigquery.ScalarQueryParameter("project_id", "STRING", project_id)


@router.get("/entities")
def list_entities(project_id: str) -> dict:
    bq = get_bigquery_client()
    rows = bq.query(
        f"SELECT * FROM `{bq.table_ref('entities')}` WHERE scenario_id = @project_id",
        params=[_project_param(project_id)],
    )
    return {"entities": rows}


@router.get("/dependencies")
def list_dependencies(project_id: str) -> dict:
    bq = get_bigquery_client()
    rows = bq.query(
        f"SELECT * FROM `{bq.table_ref('dependencies')}` WHERE scenario_id = @project_id",
        params=[_project_param(project_id)],
    )
    return {"dependencies": rows}


@router.get("/evidence")
def list_evidence(dependency_id: str) -> dict:
    bq = get_bigquery_client()
    rows = bq.query(
        f"SELECT * FROM `{bq.table_ref('evidence')}` WHERE dependency_id = @dependency_id",
        params=[bigquery.ScalarQueryParameter("dependency_id", "STRING", dependency_id)],
    )
    return {"evidence": rows}


@router.get("/waves/{project_id}")
def list_waves(project_id: str) -> dict:
    bq = get_bigquery_client()
    rows = bq.query(
        f"SELECT * FROM `{bq.table_ref('migration_waves')}` WHERE scenario_id = @project_id",
        params=[_project_param(project_id)],
    )
    return {"waves": rows}
