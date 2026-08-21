import asyncio
from io import BytesIO

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


def build_pipeline_fixture_pdf() -> bytes:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    stream = BytesIO()
    document = canvas.Canvas(stream, pagesize=(420, 594))
    document.setFont("STSong-Light", 11)
    lines = [
        "财政部关于印发《测试呆账办法（2026年版）》的通知",
        "财金〔2026〕2号",
        "时间：2026-01-15",
        "测试呆账办法（2026年版）",
        "第一条 为规范金融企业呆账核销管理，制定本办法。",
        "第二条 本办法适用于依法设立的金融企业。金融企业应当建立核销管理机制。",
        "本办法自2026年3月1日起施行。",
    ]
    y = 550
    for line in lines:
        document.drawString(24, y, line)
        y -= 20
    document.save()
    return stream.getvalue()


def test_s1_to_s4_pipeline_generates_traceable_review_results(tmp_path, monkeypatch):
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
        task = asyncio.run(
            request("POST", "/api/tasks", json={"task_id": "PIPELINE_TASK", "task_name": "测试法规解读任务"})
        )
        assert task.status_code == 201, task.text

        imported = asyncio.run(
            request(
                "POST",
                "/api/regulations/import",
                files={"file": ("测试呆账办法（2026年版）.pdf", build_pipeline_fixture_pdf(), "application/pdf")},
                data={"task_id": "PIPELINE_TASK", "version_label": "2026年版"},
            )
        )
        assert imported.status_code == 201, imported.text
        regulation_id = imported.json()["regulation"]["regulation_id"]

        result = asyncio.run(
            request(
                "POST",
                "/api/tasks/PIPELINE_TASK/interpret",
                json={"institution_type": "商业银行", "business_scope": ["呆账核销"], "region": "中国境内"},
            )
        )
        assert result.status_code == 200, result.text
        payload = result.json()
        assert payload["stages"]["S1"]["status"] == "completed"
        assert payload["stages"]["S2"]["status"] == "completed"
        assert payload["stages"]["S3"]["status"] == "completed"
        assert payload["stages"]["S4"]["status"] == "completed"
        assert payload["stages"]["S5"]["status"] == "skipped"
        assert payload["task"]["task_status"] == "waiting_review"
        assert payload["task"]["current_step"] == "S4"
        assert payload["stages"]["S2"]["output"]["status"] == "DIRECTLY_APPLICABLE"
        assert payload["requirements"]
        assert payload["article_interpretations"]
        assert all(item["review_status"] == "needs_review" for item in payload["requirements"])
        assert all({"FACT", "OFFICIAL", "INTERPRETATION"}.issubset({block["label"] for block in item["content_blocks"]}) for item in payload["article_interpretations"])
        assert all(item["evidence_ids"] for block in payload["overall"]["content_blocks"] for item in [block])
        assert payload["overall"]["regulation_id"] == regulation_id

        fetched = asyncio.run(request("GET", "/api/tasks/PIPELINE_TASK/interpretation"))
        assert fetched.status_code == 200
        assert fetched.json()["pipeline_run_id"] == payload["pipeline_run_id"]
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
