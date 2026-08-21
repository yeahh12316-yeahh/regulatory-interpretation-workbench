import asyncio

import httpx

from backend.app.main import app


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
    response = asyncio.run(request("/ready"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "mode": "scaffold",
        "database": "deferred",
        "queue": "deferred",
    }
