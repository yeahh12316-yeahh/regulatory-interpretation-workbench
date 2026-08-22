import asyncio
from datetime import date
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
from backend.app.services.ocr_fallback import OCRUnavailableError
from backend.app.services.regulation_ingest import ParsedArticle, ParsedRegulation, parse_pdf


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


def build_blank_pdf() -> bytes:
    stream = BytesIO()
    document = canvas.Canvas(stream, pagesize=(420, 594))
    document.showPage()
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


def test_public_guest_mode_allows_anonymous_isolated_api(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def db_override():
        with Session(engine) as session:
            yield session

    async def request(method: str, path: str, **kwargs):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    monkeypatch.setenv("PRIVATE_MODE", "false")
    monkeypatch.setenv("PUBLIC_GUEST_MODE", "true")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = db_override
    try:
        guest = asyncio.run(request("POST", "/api/auth/guest"))
        assert guest.status_code == 200, guest.text
        token = guest.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        regulation = asyncio.run(
            request("POST", "/api/regulations", json={"title": "公开匿名法规", "issuer": ["测试机关"]}, headers=headers)
        )
        assert regulation.status_code == 201, regulation.text
        listed = asyncio.run(request("GET", "/api/regulations", headers=headers))
        assert listed.status_code == 200
        assert listed.json()[0]["title"] == "公开匿名法规"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_scanned_pdf_uses_ocr_fallback_and_keeps_page_evidence(tmp_path, monkeypatch):
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
    monkeypatch.setenv("ENABLE_OCR_FALLBACK", "true")
    monkeypatch.setattr(
        "backend.app.services.regulation_ingest.extract_ocr_pages",
        lambda path, page_numbers: {
            1: "财政部关于印发《测试扫描办法（2026年版）》的通知\n财金〔2026〕2号\n时间：2026-02-01\n测试扫描办法（2026年版）\n第一条 为规范扫描测试业务，制定本办法。"
        },
    )
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = db_override
    try:
        registration = asyncio.run(
            request(
                "POST",
                "/api/auth/register",
                json={
                    "email": "ocr-owner@example.com",
                    "password": "correct-horse-battery-staple",
                    "display_name": "OCR Owner",
                    "organization_name": "OCR 测试机构",
                    "organization_slug": "ocr-test",
                },
            )
        )
        headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
        response = asyncio.run(
            request(
                "POST",
                "/api/regulations/import",
                headers=headers,
                files={"file": ("扫描法规.pdf", build_blank_pdf(), "application/pdf")},
                data={"version_label": "2026年版"},
            )
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["article_count"] == 1
        assert payload["sample_articles"][0]["source_page"] == 1
        assert payload["sample_articles"][0]["source_offset"]["extraction_method"] == "ocr"
        assert payload["source_document"]["document_metadata"]["extraction_summary"]["ocr_pages"] == [1]
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_cam_scanner_text_layer_triggers_ocr_and_strips_leading_scan_noise(tmp_path, monkeypatch):
    class FakePage:
        def extract_text(self):
            return "Scanned by CamScanner"

    class FakeReader:
        pages = [FakePage()]

    monkeypatch.setattr("backend.app.services.regulation_ingest.PdfReader", lambda path: FakeReader())
    monkeypatch.setattr(
        "backend.app.services.regulation_ingest.extract_ocr_pages",
        lambda path, page_numbers: {1: ".第二十四条 金融企业可以根据本办法制定实施细则。"},
    )
    path = tmp_path / "cam-scanner.pdf"
    path.write_bytes(b"placeholder")

    parsed = parse_pdf(path)

    assert [article.article_no for article in parsed.articles] == ["第二十四条"]
    assert parsed.articles[0].source_offset["extraction_method"] == "ocr"
    assert parsed.extraction_summary["ocr_pages"] == [1]


def test_scanned_pdf_without_ocr_does_not_register_empty_version(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def db_override():
        with Session(engine) as session:
            yield session

    async def request(method: str, path: str, **kwargs):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    def unavailable(path, page_numbers):
        raise OCRUnavailableError("OCR 兜底不可用，缺少命令：tesseract")

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENABLE_OCR_FALLBACK", "true")
    monkeypatch.setattr("backend.app.services.regulation_ingest.extract_ocr_pages", unavailable)
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = db_override
    try:
        registration = asyncio.run(
            request(
                "POST",
                "/api/auth/register",
                json={
                    "email": "ocr-missing-owner@example.com",
                    "password": "correct-horse-battery-staple",
                    "display_name": "OCR Missing Owner",
                    "organization_name": "OCR 缺失测试机构",
                    "organization_slug": "ocr-missing-test",
                },
            )
        )
        headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
        response = asyncio.run(
            request(
                "POST",
                "/api/regulations/import",
                headers=headers,
                files={"file": ("缺少OCR法规.pdf", build_blank_pdf(), "application/pdf")},
            )
        )
        assert response.status_code == 422, response.text
        detail = response.json()["detail"]
        assert detail["retryable"] is True
        assert "OCR" in detail["message"] or "条款" in detail["message"]
        assert (tmp_path / "documents" / detail["document_id"] / "缺少OCR法规.pdf").exists()
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_failed_parse_keeps_uploaded_file_and_retry_can_complete_import(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def db_override():
        with Session(engine) as session:
            yield session

    async def request(method: str, path: str, **kwargs):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    parsed = ParsedRegulation(
        title="可恢复测试办法（2026年版）",
        document_no="财金〔2026〕3号",
        issuer=["财政部"],
        publish_date=date(2026, 2, 1),
        effective_date=date(2026, 3, 1),
        version_label="2026年版",
        page_count=1,
        articles=[
            ParsedArticle(
                article_no="第一条",
                chapter_no=None,
                article_order=1,
                original_text="为验证失败后重试，制定本办法。",
                source_page=1,
                source_offset={"page": 1, "line_start": 1, "line_end": 1, "extraction_method": "pypdf"},
            )
        ],
        warnings=[],
        extraction_summary={"pypdf_pages": [1], "ocr_pages": [], "page_diagnostics": []},
    )
    parse_calls = {"count": 0}

    def parse_with_one_failure(path, **kwargs):
        parse_calls["count"] += 1
        if parse_calls["count"] == 1:
            raise ValueError("模拟解析失败")
        return parsed

    monkeypatch.setattr("backend.app.api.ingest.parse_pdf", parse_with_one_failure)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = db_override
    try:
        registration = asyncio.run(
            request(
                "POST",
                "/api/auth/register",
                json={
                    "email": "retry-owner@example.com",
                    "password": "correct-horse-battery-staple",
                    "display_name": "Retry Owner",
                    "organization_name": "Retry 测试机构",
                    "organization_slug": "retry-test",
                },
            )
        )
        headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
        failed = asyncio.run(
            request(
                "POST",
                "/api/regulations/import",
                headers=headers,
                files={"file": ("可恢复法规.pdf", build_blank_pdf(), "application/pdf")},
            )
        )
        assert failed.status_code == 422, failed.text
        document_id = failed.json()["detail"]["document_id"]
        storage_path = tmp_path / "documents" / document_id / "可恢复法规.pdf"
        assert storage_path.exists()
        assert failed.json()["detail"]["retryable"] is True

        retried = asyncio.run(
            request(
                "POST",
                f"/api/source-documents/{document_id}/retry-parse",
                headers=headers,
            )
        )
        assert retried.status_code == 201, retried.text
        assert retried.json()["article_count"] == 1
        assert retried.json()["source_document"]["document_metadata"]["parse_status"] == "parsed"
        assert parse_calls["count"] == 2
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
