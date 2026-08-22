"""Validate and replay the benchmark manifest without external services."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


INSTITUTION_TYPES = {"BANK", "CONSUMER_FINANCE", "FINANCE_COMPANY"}
LAYOUT_TYPES = {"official_web_pdf", "single_column_pdf", "two_column_pdf", "scanned_pdf", "attachment_heavy_pdf", "ocr_noise_pdf"}
RISK_TYPES = {"asset_quality", "credit_risk", "operational_risk", "market_risk"}


def load_manifest(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _article_count(path: Path) -> int:
    if path.suffix.lower() != ".txt":
        return 0
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"第[一二三四五六七八九十百千万两0-9]+条", text))


def validate_manifest(manifest: dict[str, Any], project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    cases = manifest.get("cases") or []
    errors: list[str] = []
    asset_errors: list[str] = []
    case_ids: set[str] = set()
    institutions: set[str] = set()
    layouts: set[str] = set()
    risks: set[str] = set()
    assertion_count = 0

    if manifest.get("schema_version") != "benchmark-v1":
        errors.append("schema_version 必须为 benchmark-v1")
    if not cases:
        errors.append("cases 不能为空")

    for case in cases:
        case_id = case.get("case_id")
        if not case_id or case_id in case_ids:
            errors.append(f"case_id 缺失或重复：{case_id}")
        case_ids.add(case_id)
        institution = case.get("institution_type")
        layout = case.get("layout_type")
        risk = case.get("risk_type")
        institutions.add(institution)
        layouts.add(layout)
        risks.add(risk)
        if institution not in INSTITUTION_TYPES:
            errors.append(f"{case_id}: 未支持的 institution_type={institution}")
        if layout not in LAYOUT_TYPES:
            errors.append(f"{case_id}: 未支持的 layout_type={layout}")
        if risk not in RISK_TYPES:
            errors.append(f"{case_id}: 未支持的 risk_type={risk}")
        source_path = root / str(case.get("source_path", ""))
        if not source_path.is_file():
            asset_errors.append(f"{case_id}: source_path 不存在：{case.get('source_path')}")
        elif source_path.suffix.lower() == ".txt" and _article_count(source_path) != (case.get("expected") or {}).get("article_count"):
            asset_errors.append(f"{case_id}: fixture 条款数与 expected.article_count 不一致")
        gold_path = case.get("gold_path")
        if gold_path and not (root / gold_path).is_file():
            asset_errors.append(f"{case_id}: gold_path 不存在：{gold_path}")
        expected = case.get("expected") or {}
        if not isinstance(expected.get("article_count"), int) or expected["article_count"] < 1:
            errors.append(f"{case_id}: expected.article_count 必须为正整数")
        if expected.get("s5_status") not in {"SKIPPED_BY_USER", "WAITING_SOURCE_VERIFICATION"}:
            errors.append(f"{case_id}: s5_status 不符合安全边界")
        assertions = case.get("assertions") or []
        if not assertions:
            errors.append(f"{case_id}: assertions 不能为空")
        assertion_count += len(assertions)

    return {
        "status": "passed" if not errors and not asset_errors else "failed",
        "case_count": len(cases),
        "institution_types": institutions,
        "layout_types": layouts,
        "risk_types": risks,
        "assertion_count": assertion_count,
        "errors": errors,
        "asset_errors": asset_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the regulatory interpretation benchmark manifest")
    parser.add_argument("--manifest", default="benchmarks/manifest.json")
    args = parser.parse_args()
    project_root = Path(args.manifest).resolve().parents[1]
    report = validate_manifest(load_manifest(args.manifest), project_root)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=list))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
