from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gcp_project_id: str = "migrationguard-sv"
    gcp_region: str = "us-central1"
    bq_dataset: str = "migrationproof"
    gcs_artifact_bucket: str = "migrationguard-sv-artifacts"
    gcs_synthetic_bucket: str = "migrationguard-sv-synthetic-data"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    dashboard_username: str = "admin"
    dashboard_password: str = ""

    environment: str = "local"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
