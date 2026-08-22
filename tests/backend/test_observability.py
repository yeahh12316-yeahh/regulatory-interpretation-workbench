import asyncio

import httpx

from backend.app.main import app


async def request(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_metrics_endpoint_is_prometheus_compatible():
    asyncio.run(request("/health"))
    response = asyncio.run(request("/metrics"))

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "# TYPE http_requests_total counter" in response.text
    assert 'route="/health"' in response.text


def test_requests_receive_a_correlation_id():
    response = asyncio.run(request("/health"))

    assert response.status_code == 200
    assert response.headers["x-request-id"]
