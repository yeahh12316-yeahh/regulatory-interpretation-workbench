import asyncio
from io import BytesIO
from types import SimpleNamespace

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
from backend.app.services.interpretation_pipeline import _extract_numbers, _version_relation, evaluate_applicability, extract_requirements


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
        "第二条 本办法适用于中国境内依法设立的金融企业。金融企业应当建立核销管理机制。",
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
        assert payload["stages"]["S5"]["output"]["comparison_status"] == "SKIPPED_NO_PREVIOUS_SOURCE"
        assert payload["stages"]["S5"]["output"]["changes"] == []
        assert payload["stages"]["S4"]["output"]["change_interpretation_status"] == "NOT_GENERATED"
        assert payload["overall"]["content_blocks"][-1]["label"] == "CHANGE"
        assert "未生成" in payload["overall"]["content_blocks"][-1]["text"]
        assert payload["task"]["task_status"] == "waiting_review"
        assert payload["task"]["current_step"] == "S4"
        assert payload["stages"]["S2"]["output"]["status"] == "DIRECTLY_APPLICABLE"
        s2_output = payload["stages"]["S2"]["output"]
        assert s2_output["regulation_locator"]["source_document_id"]
        assert s2_output["regulation_locator"]["source_hash"]
        assert s2_output["applicability_evidence"]
        assert s2_output["version_relation"]["status"] == "NO_REGISTERED_PREVIOUS"
        assert s2_output["version_relation"]["evidence_required"] is True
        assert payload["requirements"]
        assert payload["article_interpretations"]
        assert [item["article_order"] for item in payload["article_interpretations"]] == sorted(item["article_order"] for item in payload["article_interpretations"])
        assert payload["article_interpretations"][0]["article_no"] == "第一条"
        assert [item["article_order"] for item in payload["requirements"]] == sorted(item["article_order"] for item in payload["requirements"])
        assert all(item["review_status"] == "needs_review" for item in payload["requirements"])
        assert all({"FACT", "OFFICIAL", "INTERPRETATION"}.issubset({block["label"] for block in item["content_blocks"]}) for item in payload["article_interpretations"])
        assert all(item["evidence_ids"] for block in payload["overall"]["content_blocks"] for item in [block])
        assert payload["overall"]["regulation_id"] == regulation_id

        fetched = asyncio.run(request("GET", "/api/tasks/PIPELINE_TASK/interpretation"))
        assert fetched.status_code == 200
        assert fetched.json()["pipeline_run_id"] == payload["pipeline_run_id"]

        compared = asyncio.run(request("POST", "/api/tasks/PIPELINE_TASK/s5/compare"))
        assert compared.status_code == 200, compared.text
        assert compared.json()["comparison"]["comparison_status"] == "SKIPPED_NO_PREVIOUS_SOURCE"
        assert compared.json()["comparison"]["changes"] == []
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_s2_applicability_distinguishes_direct_potential_not_applicable_and_unknown():
    direct = evaluate_applicability(
        "互联网贷款管理办法",
        "本办法适用于商业银行开展互联网贷款业务。",
        "商业银行",
        "中国境内",
        business_scope=["互联网贷款"],
    )
    assert direct["status"] == "DIRECTLY_APPLICABLE"
    assert direct["matching_stage"]["business_scope_match"] is True

    potential = evaluate_applicability(
        "互联网贷款管理办法",
        "本办法适用于商业银行开展互联网贷款业务。",
        "商业银行",
        "中国境内",
        business_scope=["信用卡"],
    )
    assert potential["status"] == "POTENTIALLY_APPLICABLE"
    assert potential["matching_stage"]["institution_type_match"] is True
    assert potential["matching_stage"]["business_scope_match"] is False

    not_applicable = evaluate_applicability(
        "外资银行专项管理办法",
        "本办法仅适用于外资银行。",
        "商业银行",
        "中国境内",
        business_scope=[],
    )
    assert not_applicable["status"] == "NOT_APPLICABLE"

    needs_review = evaluate_applicability(
        "金融监管通知",
        "请关注相关事项。",
        "商业银行",
        "中国境内",
        business_scope=[],
    )
    assert needs_review["status"] == "NEEDS_REVIEW"
    assert needs_review["evidence_required"] is True


def test_s2_does_not_treat_a_previous_version_reference_as_verified():
    version = SimpleNamespace(
        previous_version_id=None,
        version_id="VER_CURRENT",
        regulation=SimpleNamespace(document_no="财金〔2026〕2号"),
    )
    relation = _version_relation(version, "本办法自2026年3月1日起施行，同时废止财金〔2025〕9号。", source_document_id="DOC_CURRENT")
    assert relation["status"] == "CANDIDATE_NEEDS_VERIFICATION"
    assert relation["candidate_previous_document_numbers"] == ["财金〔2025〕9号"]
    assert relation["from_version_id"] is None
    assert relation["evidence_required"] is True


def test_s3_splits_atomic_actions_and_preserves_exact_numeric_expressions():
    article = SimpleNamespace(
        article_id="ARTICLE_S3",
        original_text=(
            "金融企业应当建立呆账损失责任认定制度，并应当报送专项审计报告。"
            "对于形成损失的，应当在呆账核销后2年内完成责任认定；年度终了后5个月内出具报告，"
            "6个月内报送情况，符合附1所列标准之一的可认定为呆账，财金〔2015〕60号同时废止。"
        ),
    )
    requirements = extract_requirements(article)
    assert len(requirements) >= 4
    assert any(item["structured_data"]["action_strength_level"] == "must" for item in requirements)
    assert any(item["structured_data"]["action_strength_level"] == "must_not" for item in requirements) is False
    all_numbers = [number["original_expression"] for item in requirements for number in item["structured_data"]["numbers"]]
    assert {"2年内", "5个月内", "6个月内", "附1", "财金〔2015〕60号"}.issubset(all_numbers)
    assert all(item["source_text"].strip() for item in requirements)
    assert any("应当" in item["structured_data"]["normative_terms"] for item in requirements)


def test_s3_number_parser_keeps_location_and_type():
    numbers = _extract_numbers("责任期限为2年内，比例不低于5%，金额不超过100万元，参照附2。")
    by_expression = {item["original_expression"]: item for item in numbers}
    assert by_expression["2年内"]["numeric_type"] == "duration"
    assert by_expression["5%"]["numeric_type"] == "percentage"
    assert by_expression["100万元"]["numeric_type"] == "amount"
    assert by_expression["附2"]["numeric_type"] == "reference"
    assert all(isinstance(item["start"], int) and isinstance(item["end"], int) for item in numbers)
