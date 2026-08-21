from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    service_name: str = "regulatory-interpretation-api"
    database_url: str = "postgresql+psycopg://regagent:change-me@postgres:5432/regagent"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    enable_s5: bool = False
    enable_ocr_fallback: bool = True
    jwt_secret: str = "dev-only-change-this-secret-32-bytes-min"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    data_dir: str = "/data/regulatory-workbench"
    private_mode: bool = False
    private_org_name: str = "私有工作台"
    private_org_slug: str = "private-workbench"
    llm_provider: str = "rule_based"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 120

    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_prefix="",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
