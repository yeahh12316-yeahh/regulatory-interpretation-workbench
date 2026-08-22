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
from backend.app.db.models import Task, WorkflowRun
from backend.app.db.session import get_db
from backend.app.main import app


def build_workflow_pdf() -> bytes:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    stream = BytesIO()
    document = canvas.Canvas(stream, pagesize=(420, 594))
    document.setFont("STSong-Light", 11)
    lines = [
        "财政部关于印发《工作流测试办法（2026年版）》的通知",
        "财金〔2026〕18号",
        "工作流测试办法（2026年版）",
        "第一条 为规范金融企业管理，制定本办法。",
        "第二条 本办法适用于中国境内依法设立的金融企业。金融企业应当建立复核机制。",
    ]
    y = 550
    for line in lines:
        document.drawString(24, y, line)
        y -= 20
    document.save()
    return stream.getvalue()


def test_workflow_progress_failure_retry_and_node_rerun(tmp_path, monkeypatch):
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
        task = asyncio.run(request("POST", "/api/tasks", json={"task_id": "WORKFLOW_TASK", "task_name": "Workflow 测试任务"}))
        assert task.status_code == 201, task.text
        imported = asyncio.run(
            request(
                "POST",
                "/api/regulations/import",
                files={"file": ("工作流测试办法（2026年版）.pdf", build_workflow_pdf(), "application/pdf")},
                data={"task_id": "WORKFLOW_TASK", "version_label": "2026年版"},
            )
        )
        assert imported.status_code == 201, imported.text

        failed = asyncio.run(
            request(
                "POST",
                "/api/tasks/WORKFLOW_TASK/workflow",
                json={"institution_type": "商业银行", "business_scope": ["复核"], "region": "中国境内", "workflow_fail_at": "S2"},
            )
        )
        assert failed.status_code == 202, failed.text
        failed_payload = failed.json()
        assert failed_payload["status"] == "failed"
        assert failed_payload["current_node"] == "S2"
        assert failed_payload["error_state"]["retryable"] is True
        assert {node["status"] for node in failed_payload["nodes"] if node["node_name"] == "S1"} == {"completed"}
        assert {node["status"] for node in failed_payload["nodes"] if node["node_name"] == "S2"} == {"failed"}

        with Session(engine) as session:
            task_row = session.get(Task, "WORKFLOW_TASK")
            task_row.processing_config = {**task_row.processing_config, "workflow_fail_at": None}
            workflow_row = session.get(WorkflowRun, failed_payload["workflow_id"])
            workflow_row.params = {**workflow_row.params, "workflow_fail_at": None}
            session.commit()

        retried = asyncio.run(request("POST", f"/api/workflows/{failed_payload['workflow_id']}/retry"))
        assert retried.status_code == 202, retried.text
        retried_payload = retried.json()
        assert retried_payload["status"] == "completed"
        assert retried_payload["progress"] == 100
        assert retried_payload["retry_count"] == 1

        rerun = asyncio.run(request("POST", f"/api/workflows/{retried_payload['workflow_id']}/rerun", json={"node_name": "S3"}))
        assert rerun.status_code == 202, rerun.text
        rerun_payload = rerun.json()
        assert rerun_payload["status"] == "completed"
        assert rerun_payload["requested_from"] == "S3"
        assert rerun_payload["parent_workflow_id"] == retried_payload["workflow_id"]
        assert all(node["status"] in {"completed", "skipped"} for node in rerun_payload["nodes"])
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
