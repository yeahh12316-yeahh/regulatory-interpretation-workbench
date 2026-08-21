import asyncio
from io import BytesIO
from pathlib import Path

import httpx
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings
from backend.app.db import model_registry  # noqa: F401
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app


def build_fixture_pdf() -> bytes:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    stream = BytesIO()
    document = canvas.Canvas(stream, pagesize=(420, 594))
    document.setFont("STSong-Light", 11)
    lines = [
        "财政部关于印发《测试金融办法（2026年版）》的通知",
        "财金〔2026〕1号",
        "时间：2026-01-15",
        "测试金融办法（2026年版）",
        "第一章 总则",
        "第一条 为规范测试金融业务，制定本办法。",
        "第二条 本办法适用于依法设立的金融企业。",
        "本办法自2026年3月1日起施行。",
    ]
    y = 550
    for line in lines:
        document.drawString(24, y, line)
        y -= 20
    document.save()
    return stream.getvalue()


def test_pdf_upload_registers_version_articles_and_source_locations(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def db_override():
        with Session(engine) as session:
            yield session

    async def request(method: str, path: str, **kwargs):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = db_override
    try:
        registration = asyncio.run(
            request(
                "POST",
                "/api/auth/register",
                json={
                    "email": "ingest-owner@example.com",
                    "password": "correct-horse-battery-staple",
                    "display_name": "Ingest Owner",
                    "organization_name": "法规解析测试机构",
                    "organization_slug": "ingest-test",
                },
            )
        )
        assert registration.status_code == 201
        headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
        pdf_name = "测试金融办法（2026年版）.pdf"
        pdf_bytes = build_fixture_pdf()
        response = asyncio.run(
            request(
                "POST",
                "/api/regulations/import",
                headers=headers,
                files={"file": (pdf_name, pdf_bytes, "application/pdf")},
                data={"version_label": "2026年版", "source_url": "https://example.com/regulation"},
            )
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["article_count"] == 2
        assert payload["page_count"] == 1
        assert payload["regulation"]["title"] == "测试金融办法(2026年版)"
        assert payload["version"]["version_label"] == "2026年版"
        assert payload["version"]["effective_date"] == "2026-03-01"
        assert payload["source_document"]["sha256"]
        assert payload["sample_articles"][0]["article_no"] == "第一条"
        assert payload["sample_articles"][0]["source_page"] == 1
        assert payload["sample_articles"][0]["source_offset"]["line_start"] > 0
        storage_path = tmp_path / "documents" / payload["source_document"]["document_id"] / pdf_name
        assert storage_path.exists()
        source_file = asyncio.run(
            request(
                "GET",
                f"/api/source-documents/{payload['source_document']['document_id']}/file",
                headers=headers,
            )
        )
        assert source_file.status_code == 200
        assert source_file.headers["content-type"] == "application/pdf"

        articles = asyncio.run(
            request(
                "GET",
                f"/api/regulations/{payload['regulation']['regulation_id']}/versions/{payload['version']['version_id']}/articles",
                headers=headers,
            )
        )
        assert articles.status_code == 200
        assert len(articles.json()) == 2
        assert articles.json()[-1]["article_no"] == "第二条"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_private_mode_allows_single_team_api_without_login(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def db_override():
        with Session(engine) as session:
            yield session

    async def request(method: str, path: str, **kwargs):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    monkeypatch.setenv("PRIVATE_MODE", "true")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = db_override
    try:
        regulation = asyncio.run(
            request("POST", "/api/regulations", json={"title": "私有模式测试法规", "issuer": ["测试机关"]})
        )
        assert regulation.status_code == 201, regulation.text
        listed = asyncio.run(request("GET", "/api/regulations"))
        assert listed.status_code == 200
        assert listed.json()[0]["title"] == "私有模式测试法规"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
