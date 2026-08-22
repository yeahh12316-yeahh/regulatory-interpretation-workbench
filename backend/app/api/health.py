from fastapi import APIRouter, Depends, HTTPException
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.session import get_db


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.service_name,
    }


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    settings = get_settings()
    queue = "deferred"
    if settings.redis_readiness_required:
        try:
            Redis.from_url(
                settings.redis_url,
                socket_connect_timeout=1,
                socket_timeout=1,
                health_check_interval=5,
            ).ping()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="queue dependency is not ready") from exc
        queue = "connected"
    return {
        "status": "ready",
        "mode": "database",
        "database": "connected",
        "queue": queue,
    }
