from fastapi import APIRouter

from backend.app.core.config import get_settings


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.service_name,
    }


@router.get("/ready")
def ready() -> dict[str, str]:
    # Step 6 establishes the boot contract. Database and queue connectivity
    # are deliberately deferred to the data/workflow steps and not faked here.
    return {
        "status": "ready",
        "mode": "scaffold",
        "database": "deferred",
        "queue": "deferred",
    }
