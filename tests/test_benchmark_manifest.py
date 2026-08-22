from pathlib import Path

from benchmarks.runner import load_manifest, validate_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_manifest_covers_institutions_layouts_and_risk_types():
    manifest = load_manifest(PROJECT_ROOT / "benchmarks/manifest.json")
    report = validate_manifest(manifest, PROJECT_ROOT)

    assert report["status"] == "passed"
    assert report["case_count"] >= 6
    assert report["institution_types"] >= {"BANK", "CONSUMER_FINANCE", "FINANCE_COMPANY"}
    assert report["layout_types"] >= {"official_web_pdf", "single_column_pdf", "two_column_pdf", "scanned_pdf"}
    assert report["risk_types"] >= {"asset_quality", "credit_risk", "operational_risk", "market_risk"}
    assert report["asset_errors"] == []


def test_benchmark_cases_have_replayable_assertions():
    manifest = load_manifest(PROJECT_ROOT / "benchmarks/manifest.json")

    for case in manifest["cases"]:
        assert case["case_id"]
        assert case["expected"]["article_count"] >= 1
        assert case["expected"]["s5_status"] in {"SKIPPED_BY_USER", "WAITING_SOURCE_VERIFICATION"}
        assert case["assertions"]
