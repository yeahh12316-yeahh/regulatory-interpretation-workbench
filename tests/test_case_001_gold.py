import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_gold() -> dict:
    return json.loads((PROJECT_ROOT / "benchmarks/gold/case-001.json").read_text(encoding="utf-8"))


def test_case_001_gold_freezes_non_s5_article_scope_and_locations():
    gold = load_gold()

    assert gold["status"] == "BODY_GOLD_BASELINE_FROZEN_METADATA_REVIEW_REQUIRED"
    assert gold["source_register"]["new_regulation"]["sha256"] == "8bd8290816f7ba9dbba81def4e725fbfccdea984a0f616f2bb00a98a6b8c2da8"
    assert [item["article"] for item in gold["article_gold"]] == list(range(1, 26))
    assert [item["page"] for item in gold["article_gold"][:4]] == [1, 1, 1, 1]
    assert [item["page"] for item in gold["article_gold"][4:15]] == [2] * 11
    assert [item["page"] for item in gold["article_gold"][15:]] == [3] * 10


def test_case_001_gold_preserves_high_risk_facts_and_s5_boundary():
    gold = load_gold()

    assert len(gold["high_risk_fact_ids"]) == 12
    assert set(gold["high_risk_fact_ids"]) == set(gold["evidence_position_gold"])
    assert {item["value"] for item in gold["numeric_gold"]} >= {"2年", "5个月", "6个月", "2017年10月1日"}
    assert gold["metadata_gold"]["attachments"]["status"] == "REFERRED_BUT_NOT_INCLUDED"
    assert gold["s5"]["status"] == "SKIPPED_BY_USER"
