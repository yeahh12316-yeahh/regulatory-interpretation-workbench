from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    service_name: str = "regulatory-interpretation-worker"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    worker_concurrency: int = 2

    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_prefix="",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
