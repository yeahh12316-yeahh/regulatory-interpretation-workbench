from types import SimpleNamespace

from backend.app.services.interpretation_s4 import build_article_fields, build_overall_fields


def _article():
    return SimpleNamespace(article_no="第一条", original_text="金融企业应当在6个月内报送情况。", source_page=2)


def _requirement():
    return SimpleNamespace(
        subject="金融企业",
        action="应当",
        object="报送情况",
        condition=None,
        exception=None,
        deadline="6个月内",
        frequency=None,
        threshold=None,
        source_text="金融企业应当在6个月内报送情况。",
        requirement_id="REQ_1",
    )


def test_s4_generates_overall_change_boundary_without_old_source():
    fields = build_overall_fields(
        regulation=SimpleNamespace(title="测试办法", issuer=["测试机关"], document_no="测文〔2026〕1号"),
        version=SimpleNamespace(version_label="2026年版", effective_date=None),
        source_document=SimpleNamespace(file_name="new.pdf", page_count=2),
        articles=[_article()],
        requirements=[_requirement()],
        applicability={"status": "DIRECTLY_APPLICABLE", "reason": "正文明确适用。"},
        s5_output={"comparison_status": "SKIPPED_NO_PREVIOUS_SOURCE", "reason": "旧规原文未提供。", "changes": [], "summary": {"counts": {"ADDED": 0, "DELETED": 0, "MODIFIED": 0}}},
        evidence_ids=["EVID_1"],
    )

    assert fields["change_interpretation_status"] == "NOT_GENERATED"
    assert fields["content_blocks"][-1]["label"] == "CHANGE"
    assert "未生成" in fields["content_blocks"][-1]["text"]
    assert fields["content_blocks"][-1]["evidence_ids"] == ["EVID_1"]


def test_s4_generates_article_change_interpretation_only_from_completed_s5():
    change = {
        "change_id": "S5-MODIFIED-第一条",
        "article_no": "第一条",
        "change_type": "MODIFIED",
        "change_dimensions": ["NUMERIC", "TIME"],
        "old_evidence": {"source_text": "金融企业应当在5个月内报送情况。", "page": 1, "source_hash": "b" * 64},
        "new_evidence": {"source_text": "金融企业应当在6个月内报送情况。", "page": 2, "source_hash": "a" * 64},
    }
    fields = build_article_fields(
        article=_article(),
        requirements=[_requirement()],
        evidence_id="EVID_1",
        s5_output={"comparison_status": "COMPLETED", "changes": [change]},
    )

    assert fields["change_interpretation_status"] == "GENERATED_NEEDS_REVIEW"
    change_block = next(block for block in fields["content_blocks"] if block["label"] == "CHANGE")
    assert "修改条款" in change_block["text"]
    assert "NUMERIC / TIME" in change_block["text"]
    assert change_block["s5_change_id"] == change["change_id"]
    assert change_block["old_evidence"]["page"] == 1
    assert fields["interpretation"].endswith("具体监管含义仍需人工复核。")
