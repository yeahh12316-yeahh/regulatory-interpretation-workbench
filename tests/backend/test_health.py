import asyncio

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.db import model_registry  # noqa: F401
from backend.app.db.base import Base
from backend.app.db.session import get_db


TEST_ENGINE = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(TEST_ENGINE)


def db_override():
    with Session(TEST_ENGINE) as session:
        yield session


async def request(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_health_endpoint_reports_liveness():
    response = asyncio.run(request("/health"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "regulatory-interpretation-api",
    }


def test_ready_endpoint_reports_scaffold_readiness_without_claiming_pipeline_ready():
    app.dependency_overrides[get_db] = db_override
    response = asyncio.run(request("/ready"))
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "mode": "database",
        "database": "connected",
        "queue": "deferred",
    }
