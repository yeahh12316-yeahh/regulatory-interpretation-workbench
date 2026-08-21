from worker.app.core.config import get_worker_settings


def heartbeat_payload() -> dict[str, str]:
    settings = get_worker_settings()
    return {
        "status": "ok",
        "service": settings.service_name,
        "mode": "scaffold",
    }
