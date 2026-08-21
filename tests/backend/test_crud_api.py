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
        regulation = asyncio.run(
            request(
                "POST",
                "/api/regulations",
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

        fetched = asyncio.run(request("GET", "/api/evidence/EVID_001"))
        assert fetched.status_code == 200
        assert fetched.json()["source_document_id"] == "DOC_001"

        missing_source = asyncio.run(
            request(
                "POST",
                "/api/evidence",
                json={
                    "source_document_id": "DOES_NOT_EXIST",
                    "source_type": "official_pdf",
                },
            )
        )
        assert missing_source.status_code == 404
    finally:
        app.dependency_overrides.clear()
