import asyncio

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.db import model_registry  # noqa: F401
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app


def test_regulations_and_source_storage_are_organization_scoped():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def db_override():
        with Session(engine) as session:
            yield session

    async def request(method: str, path: str, **kwargs):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    app.dependency_overrides[get_db] = db_override
    try:
        first = asyncio.run(request("POST", "/api/auth/register", json={
            "email": "benchmark-security-first@example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "First",
            "organization_name": "第一机构",
            "organization_slug": "benchmark-security-first",
        }))
        second = asyncio.run(request("POST", "/api/auth/register", json={
            "email": "benchmark-security-second@example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "Second",
            "organization_name": "第二机构",
            "organization_slug": "benchmark-security-second",
        }))
        first_headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}

        regulation = asyncio.run(request("POST", "/api/regulations", headers=first_headers, json={
            "regulation_id": "SECURITY_REGULATION_001",
            "title": "机构隔离测试办法",
            "document_no": "测〔2026〕1号",
            "issuer": ["测试机关"],
        }))
        assert regulation.status_code == 201, regulation.text

        hidden_regulation = asyncio.run(request("GET", "/api/regulations/SECURITY_REGULATION_001", headers=second_headers))
        assert hidden_regulation.status_code == 404
        hidden_list = asyncio.run(request("GET", "/api/regulations", headers=second_headers))
        assert hidden_list.status_code == 200
        assert "SECURITY_REGULATION_001" not in {item["regulation_id"] for item in hidden_list.json()}

        cross_org_task = asyncio.run(request("POST", "/api/tasks", headers=second_headers, json={
            "task_id": "SECURITY_CROSS_ORG_TASK",
            "task_name": "跨机构法规引用",
            "regulation_id": "SECURITY_REGULATION_001",
        }))
        assert cross_org_task.status_code == 404

        unsafe_source = asyncio.run(request("POST", "/api/source-documents", headers=first_headers, json={
            "document_id": "SECURITY_UNSAFE_SOURCE",
            "file_name": "test.pdf",
            "source_type": "official_pdf",
            "storage_key": "../outside/test.pdf",
            "sha256": "a" * 64,
        }))
        assert unsafe_source.status_code == 422
    finally:
        app.dependency_overrides.clear()
