from fastapi import APIRouter, Depends, UploadFile

from app.auth.dependencies import require_session
from app.storage.gcs_client import get_gcs_client

router = APIRouter(prefix="/artifacts", tags=["artifacts"], dependencies=[Depends(require_session)])


@router.post("/upload/{project_id}")
async def upload_artifact(project_id: str, file: UploadFile) -> dict:
    gcs = get_gcs_client()
    content = await file.read()
    uri = gcs.upload_artifact(project_id, file.filename, content)
    return {"project_id": project_id, "filename": file.filename, "gcs_uri": uri}


@router.get("/{project_id}")
def list_artifacts(project_id: str) -> dict:
    gcs = get_gcs_client()
    return {"project_id": project_id, "artifacts": gcs.list_artifacts(project_id)}


@router.delete("/{project_id}/{filename}")
def delete_artifact(project_id: str, filename: str) -> dict:
    gcs = get_gcs_client()
    gcs.delete_artifact(project_id, filename)
    return {"project_id": project_id, "filename": filename, "deleted": True}


@router.delete("/{project_id}")
def delete_all_artifacts(project_id: str) -> dict:
    gcs = get_gcs_client()
    count = gcs.delete_all_artifacts(project_id)
    return {"project_id": project_id, "deleted_count": count}
