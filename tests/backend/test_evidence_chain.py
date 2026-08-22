import asyncio
from io import BytesIO

import httpx
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings
from backend.app.db import model_registry  # noqa: F401
from backend.app.db.base import Base
from backend.app.db.models import ContentVersion
from backend.app.db.session import get_db
from backend.app.main import app


def _pdf() -> bytes:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    stream = BytesIO()
    document = canvas.Canvas(stream, pagesize=(420, 594))
    document.setFont("STSong-Light", 11)
    lines = [
        "财政部关于印发《测试证据办法（2026年版）》的通知",
        "财金〔2026〕9号",
        "测试证据办法（2026年版）",
        "第一条 为规范金融企业管理，制定本办法。",
        "第二条 本办法适用于中国境内依法设立的金融企业。金融企业应当建立证据机制。",
        "本办法自2026年3月1日起施行。",
    ]
    y = 550
    for line in lines:
        document.drawString(24, y, line)
        y -= 20
    document.save()
    return stream.getvalue()


def test_content_package_requires_verified_chain_and_keeps_locked_versions(tmp_path, monkeypatch):
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
        created = asyncio.run(request("POST", "/api/tasks", json={"task_id": "EVIDENCE_TASK", "task_name": "证据链测试任务"}))
        assert created.status_code == 201, created.text
        imported = asyncio.run(
            request(
                "POST",
                "/api/regulations/import",
                files={"file": ("测试证据办法（2026年版）.pdf", _pdf(), "application/pdf")},
                data={"task_id": "EVIDENCE_TASK", "version_label": "2026年版"},
            )
        )
        assert imported.status_code == 201, imported.text
        interpreted = asyncio.run(
            request("POST", "/api/tasks/EVIDENCE_TASK/interpret", json={"institution_type": "商业银行", "business_scope": ["证据"], "region": "中国境内"})
        )
        assert interpreted.status_code == 200, interpreted.text
        payload = interpreted.json()

        blocked = asyncio.run(request("POST", "/api/tasks/EVIDENCE_TASK/content-package"))
        assert blocked.status_code == 409, blocked.text
        assert "interpretations_not_locked" in blocked.json()["detail"]["missing"]

        for requirement in payload["requirements"]:
            response = asyncio.run(
                request(
                    "PATCH",
                    f"/api/tasks/EVIDENCE_TASK/review/requirements/{requirement['requirement_id']}",
                    json={"review_status": "reviewed"},
                )
            )
            assert response.status_code == 200, response.text
        for interpretation in [payload["overall"], *payload["article_interpretations"]]:
            response = asyncio.run(
                request(
                    "PATCH",
                    f"/api/tasks/EVIDENCE_TASK/review/interpretations/{interpretation['interpretation_id']}",
                    json={"review_status": "reviewed", "human_lock": True},
                )
            )
            assert response.status_code == 200, response.text
        for evidence in payload["evidence"]:
            response = asyncio.run(
                request(
                    "PATCH",
                    f"/api/tasks/EVIDENCE_TASK/review/evidence/{evidence['evidence_id']}",
                    json={"verification_status": "verified"},
                )
            )
            assert response.status_code == 200, response.text

        package = asyncio.run(request("POST", "/api/tasks/EVIDENCE_TASK/content-package"))
        assert package.status_code == 201, package.text
        package_payload = package.json()
        assert package_payload["status"] == "HUMAN_LOCKED"
        assert package_payload["package_version"] == 1
        assert len(package_payload["content"]["evidence_links"]) >= len(payload["evidence"])
        assert len(package_payload["content_hash"]) == 64
        assert package_payload["content"]["overview"]["interpretation_id"] == payload["overall"]["interpretation_id"]

        locked_update = asyncio.run(
            request(
                "PATCH",
                f"/api/tasks/EVIDENCE_TASK/review/interpretations/{payload['overall']['interpretation_id']}",
                json={"interpretation": "不应覆盖锁定版本。", "review_status": "reviewed", "human_lock": True},
            )
        )
        assert locked_update.status_code == 409, locked_update.text

        with Session(engine) as session:
            snapshots = list(session.scalars(select(ContentVersion).where(ContentVersion.task_id == "EVIDENCE_TASK")))
            assert snapshots
            assert any(item.status == "HUMAN_LOCKED" and item.content_hash for item in snapshots)
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
