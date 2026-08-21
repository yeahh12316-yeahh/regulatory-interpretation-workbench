import asyncio

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.db import model_registry  # noqa: F401
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app


ENGINE = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(ENGINE)


def db_override():
    with Session(ENGINE) as session:
        yield session


async def request(method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_minimal_task_regulation_source_and_evidence_crud():
    app.dependency_overrides[get_db] = db_override
    try:
        registration = asyncio.run(
            request(
                "POST",
                "/api/auth/register",
                json={
                    "email": "owner@example.com",
                    "password": "correct-horse-battery-staple",
                    "display_name": "Owner",
                    "organization_name": "测试机构",
                    "organization_slug": "test-org",
                },
            )
        )
        assert registration.status_code == 201
        headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
        regulation = asyncio.run(
            request(
                "POST",
                "/api/regulations",
                headers=headers,
                json={
                    "regulation_id": "FIN_MOF_2017_90",
                    "title": "金融企业呆账核销管理办法（2017年版）",
                    "document_no": "财金〔2017〕90号",
                    "issuer": ["财政部"],
                    "applicable_entities": ["商业银行"],
                },
            )
        )
        assert regulation.status_code == 201

        task = asyncio.run(
            request(
                "POST",
                "/api/tasks",
                headers=headers,
                json={
                    "task_id": "TASK_001",
                    "task_name": "呆账核销管理办法解读",
                    "created_by": "tester",
                    "regulation_id": "FIN_MOF_2017_90",
                },
            )
        )
        assert task.status_code == 201
        assert task.json()["task_status"] == "created"

        source = asyncio.run(
            request(
                "POST",
                "/api/source-documents",
                headers=headers,
                json={
                    "document_id": "DOC_001",
                    "task_id": "TASK_001",
                    "file_name": "2017.pdf",
                    "source_type": "official_pdf",
                    "storage_key": "sources/2017.pdf",
                    "sha256": "8bd8290816f7ba9dbba81def4e725fbfccdea984a0f616f2bb00a98a6b8c2da8",
                    "page_count": 4,
                },
            )
        )
        assert source.status_code == 201

        evidence = asyncio.run(
            request(
                "POST",
                "/api/evidence",
                headers=headers,
                json={
                    "evidence_id": "EVID_001",
                    "task_id": "TASK_001",
                    "regulation_id": "FIN_MOF_2017_90",
                    "source_document_id": "DOC_001",
                    "source_type": "official_pdf",
                    "locator": {"page": 1, "article_no": "第一条"},
                    "source_text": "为加强金融企业呆账核销管理，制定本办法。",
                    "verification_status": "verified",
                },
            )
        )
        assert evidence.status_code == 201
        assert evidence.json()["locator"]["page"] == 1

        fetched = asyncio.run(request("GET", "/api/evidence/EVID_001", headers=headers))
        assert fetched.status_code == 200
        assert fetched.json()["source_document_id"] == "DOC_001"

        missing_source = asyncio.run(
            request(
                "POST",
                "/api/evidence",
                headers=headers,
                json={
                    "source_document_id": "DOES_NOT_EXIST",
                    "source_type": "official_pdf",
                },
            )
        )
        assert missing_source.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_authentication_organization_membership_and_task_isolation():
    app.dependency_overrides[get_db] = db_override
    try:
        first = asyncio.run(
            request(
                "POST",
                "/api/auth/register",
                json={
                    "email": "first@example.com",
                    "password": "correct-horse-battery-staple",
                    "display_name": "First",
                    "organization_name": "机构一",
                    "organization_slug": "org-one",
                },
            )
        )
        second = asyncio.run(
            request(
                "POST",
                "/api/auth/register",
                json={
                    "email": "second@example.com",
                    "password": "correct-horse-battery-staple",
                    "display_name": "Second",
                    "organization_name": "机构二",
                    "organization_slug": "org-two",
                },
            )
        )
        first_headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}

        task = asyncio.run(
            request(
                "POST",
                "/api/tasks",
                headers=first_headers,
                json={"task_id": "ORG_ONE_TASK", "task_name": "机构一任务"},
            )
        )
        assert task.status_code == 201
        assert task.json()["organization_id"] == first.json()["organization_id"]

        hidden = asyncio.run(request("GET", "/api/tasks/ORG_ONE_TASK", headers=second_headers))
        assert hidden.status_code == 404

        me = asyncio.run(request("GET", "/api/auth/me", headers=first_headers))
        assert me.status_code == 200
        assert me.json()["email"] == "first@example.com"

        add_member = asyncio.run(
            request(
                "POST",
                "/api/organizations/current/members",
                headers=first_headers,
                json={"email": "second@example.com", "role": "viewer"},
            )
        )
        assert add_member.status_code == 201

        switched = asyncio.run(
            request(
                "POST",
                "/api/auth/switch-organization",
                headers=second_headers,
                json={"organization_id": first.json()["organization_id"]},
            )
        )
        assert switched.status_code == 200
        second_org_headers = {"Authorization": f"Bearer {switched.json()['access_token']}"}
        viewer_read = asyncio.run(request("GET", "/api/tasks/ORG_ONE_TASK", headers=second_org_headers))
        assert viewer_read.status_code == 200
        viewer_write = asyncio.run(
            request(
                "POST",
                "/api/tasks",
                headers=second_org_headers,
                json={"task_name": "viewer cannot create"},
            )
        )
        assert viewer_write.status_code == 403

        role_update = asyncio.run(
            request(
                "PATCH",
                f"/api/organizations/current/members/{add_member.json()['member_id']}",
                headers=first_headers,
                json={"role": "editor"},
            )
        )
        assert role_update.status_code == 200
        editor_write = asyncio.run(
            request(
                "POST",
                "/api/tasks",
                headers=second_org_headers,
                json={"task_name": "editor can create"},
            )
        )
        assert editor_write.status_code == 201

        unauthorized = asyncio.run(request("GET", "/api/tasks/ORG_ONE_TASK"))
        assert unauthorized.status_code == 401
    finally:
        app.dependency_overrides.clear()
