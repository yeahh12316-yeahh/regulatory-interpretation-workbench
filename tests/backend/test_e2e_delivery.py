import asyncio
from io import BytesIO

import httpx
from docx import Document
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


def build_e2e_pdf() -> bytes:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    stream = BytesIO()
    document = canvas.Canvas(stream, pagesize=(420, 594))
    document.setFont("STSong-Light", 11)
    lines = [
        "财政部关于印发《端到端验收办法（2026年版）》的通知",
        "财金〔2026〕28号",
        "时间：2026-01-15",
        "端到端验收办法（2026年版）",
        "第一条 为规范金融企业管理，制定本办法。",
        "第二条 本办法适用于中国境内依法设立的金融企业。金融企业应当建立复核机制。",
        "本办法自2026年3月1日起施行。",
    ]
    y = 550
    for line in lines:
        document.drawString(24, y, line)
        y -= 20
    document.save()
    return stream.getvalue()


def test_workflow_to_review_to_html_and_word_delivery(tmp_path, monkeypatch):
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
    monkeypatch.setenv("WORKFLOW_EXECUTION_MODE", "inline")
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = db_override
    try:
        task = asyncio.run(request("POST", "/api/tasks", json={"task_id": "E2E_DELIVERY_TASK", "task_name": "端到端交付验收"}))
        assert task.status_code == 201, task.text
        imported = asyncio.run(request(
            "POST",
            "/api/regulations/import",
            files={"file": ("端到端验收办法（2026年版）.pdf", build_e2e_pdf(), "application/pdf")},
            data={"task_id": "E2E_DELIVERY_TASK", "version_label": "2026年版"},
        ))
        assert imported.status_code == 201, imported.text

        workflow = asyncio.run(request(
            "POST",
            "/api/tasks/E2E_DELIVERY_TASK/workflow",
            json={"institution_type": "商业银行", "business_scope": ["复核"], "region": "中国境内"},
        ))
        assert workflow.status_code == 202, workflow.text
        assert workflow.json()["status"] == "completed"
        assert workflow.json()["progress"] == 100

        review = asyncio.run(request("GET", "/api/tasks/E2E_DELIVERY_TASK/review"))
        assert review.status_code == 200, review.text
        payload = review.json()
        for requirement in payload["requirements"]:
            response = asyncio.run(request(
                "PATCH",
                f"/api/tasks/E2E_DELIVERY_TASK/review/requirements/{requirement['requirement_id']}",
                json={"review_status": "reviewed"},
            ))
            assert response.status_code == 200, response.text
        for interpretation in [payload["overall"], *payload["article_interpretations"]]:
            response = asyncio.run(request(
                "PATCH",
                f"/api/tasks/E2E_DELIVERY_TASK/review/interpretations/{interpretation['interpretation_id']}",
                json={"review_status": "reviewed", "human_lock": True},
            ))
            assert response.status_code == 200, response.text
        for evidence in payload["evidence"]:
            response = asyncio.run(request(
                "PATCH",
                f"/api/tasks/E2E_DELIVERY_TASK/review/evidence/{evidence['evidence_id']}",
                json={"verification_status": "verified"},
            ))
            assert response.status_code == 200, response.text

        qc = asyncio.run(request("POST", "/api/tasks/E2E_DELIVERY_TASK/review/qc"))
        assert qc.status_code == 200, qc.text
        assert qc.json()["status"] == "passed", qc.text
        export = asyncio.run(request("POST", "/api/tasks/E2E_DELIVERY_TASK/export/docx"))
        assert export.status_code == 200, export.text
        export_payload = export.json()
        assert export_payload["consistency"]["status"] == "passed"

        word = asyncio.run(request("GET", export_payload["download_url"]))
        html = asyncio.run(request("GET", export_payload["html_download_url"]))
        assert word.status_code == 200 and word.content[:2] == b"PK"
        assert html.status_code == 200 and "data-content-hash" in html.text
        rendered = Document(BytesIO(word.content))
        word_text = "\n".join(paragraph.text for paragraph in rendered.paragraphs)
        assert export_payload["consistency"]["content_hash"] in word_text
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
