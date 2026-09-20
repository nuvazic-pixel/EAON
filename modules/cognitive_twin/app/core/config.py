from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Personal Cognitive Twin — Genesis"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://twin:change-me-local-only@db:5432/cognitive_twin"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    twin_subject_id: str = "self"
    excluded_domains: str = "work,professional,employment"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def excluded_domain_set(self) -> set[str]:
        return {x.strip().lower() for x in self.excluded_domains.split(",") if x.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
