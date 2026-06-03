from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    api_version: str = "v1"
    database_url: str = (
        "postgresql+psycopg://enviro_nexus:enviro_nexus_dev"
        "@localhost:15432/enviro_nexus_knowledge"
    )
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
