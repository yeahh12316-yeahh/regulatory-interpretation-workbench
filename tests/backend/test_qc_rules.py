from types import SimpleNamespace

from backend.app.services.qc_rules import run_rule_checks


def test_rule_qc_catches_source_numeric_and_language_risks():
    article = SimpleNamespace(original_text="第二条 金融企业应当在2026年3月1日起建立复核机制。")
    requirement = SimpleNamespace(
        requirement_id="REQ-1",
        source_text="金融企业应当在2026年3月1日起建立复核机制。",
        article=article,
        structured_data={"numbers": []},
    )
    interpretation = SimpleNamespace(
        interpretation_id="INT-1",
        summary="全面提升管理水平",
        interpretation="",
        regulatory_meaning="",
        content_blocks=[{"label": "UNKNOWN", "text": "结论", "evidence_ids": ["E-MISSING"]}],
    )
    evidence = SimpleNamespace(
        evidence_id="E-1",
        locator={"source_sha256": "wrong"},
        source_document=SimpleNamespace(sha256="right"),
    )

    findings = run_rule_checks({"overall": interpretation, "article_interpretations": [], "requirements": [requirement], "evidence": [evidence]})
    codes = {item["code"] for item in findings}
    assert "NUMERIC_EXPRESSION_NOT_STRUCTURED" in codes
    assert "CONTENT_BLOCK_LABEL_INVALID" in codes
    assert "INTERPRETATION_ABSOLUTE_LANGUAGE" in codes
    assert "EVIDENCE_SOURCE_HASH_MISMATCH" in codes
