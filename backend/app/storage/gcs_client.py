"""Thin wrapper around google-cloud-storage for artifact and synthetic-data buckets."""
from functools import lru_cache

from google.cloud import storage

from app.config import get_settings


class GCSClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = storage.Client(project=settings.gcp_project_id)
        self.artifact_bucket_name = settings.gcs_artifact_bucket
        self.synthetic_bucket_name = settings.gcs_synthetic_bucket

    def upload_artifact(self, project_id: str, filename: str, content: bytes) -> str:
        bucket = self.client.bucket(self.artifact_bucket_name)
        blob_path = f"{project_id}/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(content)
        return f"gs://{self.artifact_bucket_name}/{blob_path}"

    def list_artifacts(self, project_id: str) -> list[str]:
        bucket = self.client.bucket(self.artifact_bucket_name)
        return [f"gs://{self.artifact_bucket_name}/{b.name}" for b in bucket.list_blobs(prefix=f"{project_id}/")]

    def download_text(self, gcs_uri: str) -> str:
        bucket_name, blob_path = self._parse_uri(gcs_uri)
        bucket = self.client.bucket(bucket_name)
        return bucket.blob(blob_path).download_as_text()

    def delete_artifact(self, project_id: str, filename: str) -> None:
        bucket = self.client.bucket(self.artifact_bucket_name)
        blob_path = f"{project_id}/{filename}"
        blob = bucket.blob(blob_path)
        if blob.exists():
            blob.delete()

    def delete_all_artifacts(self, project_id: str) -> int:
        bucket = self.client.bucket(self.artifact_bucket_name)
        blobs = list(bucket.list_blobs(prefix=f"{project_id}/"))
        for blob in blobs:
            blob.delete()
        return len(blobs)

    def upload_synthetic(self, scenario_id: str, filename: str, content: bytes) -> str:
        bucket = self.client.bucket(self.synthetic_bucket_name)
        blob_path = f"{scenario_id}/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(content)
        return f"gs://{self.synthetic_bucket_name}/{blob_path}"

    @staticmethod
    def _parse_uri(gcs_uri: str) -> tuple[str, str]:
        assert gcs_uri.startswith("gs://"), f"Not a GCS URI: {gcs_uri}"
        without_scheme = gcs_uri[len("gs://"):]
        bucket_name, _, blob_path = without_scheme.partition("/")
        return bucket_name, blob_path


@lru_cache
def get_gcs_client() -> GCSClient:
    return GCSClient()
