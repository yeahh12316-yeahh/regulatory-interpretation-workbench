from functools import lru_cache

from pydantic import field_validator
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
    web_origin: str = "http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:18080"
    private_mode: bool = False
    public_guest_mode: bool = False
    private_org_name: str = "私有工作台"
    private_org_slug: str = "private-workbench"
    llm_provider: str = "rule_based"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 120
    llm_reviewer_required: bool = False
    redis_readiness_required: bool = False
    log_format: str = "text"
    prometheus_enabled: bool = True
    workflow_execution_mode: str = "celery"
    workflow_allow_inline_fallback: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgres_driver(cls, value: str) -> str:
        """Use the installed psycopg 3 driver for provider connection URLs.

        Managed Postgres providers commonly expose ``postgres://`` or
        ``postgresql://`` URLs. SQLAlchemy otherwise defaults those URLs to
        the uninstalled psycopg2 driver, even though this project ships
        psycopg 3.
        """

        if not isinstance(value, str):
            return value
        for prefix in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    model_config = SettingsConfigDict(
        # Local secrets belong in the ignored .env.local; .env remains the
        # shared non-secret fallback for Docker and development defaults.
        env_file=(".env", ".env.local"),
        env_prefix="",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
