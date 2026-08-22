"""Deterministic quality rules for the human-review release gate.

These checks are deliberately conservative.  A rule can block delivery when
the source/evidence relationship is objectively broken, but it must not turn
an interpretation preference into a fabricated legal conclusion.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.services.interpretation_pipeline import _extract_numbers


ALLOWED_BLOCK_LABELS = {"FACT", "OFFICIAL", "INTERPRETATION", "CHANGE"}
ABSOLUTE_LANGUAGE = (
    "全面提升",
    "重大突破",
    "全面重塑",
    "史上最严",
    "根本改变",
    "深刻影响",
    "极大促进",
    "显著增强",
    "彻底解决",
    "前所未有",
)


def _compact(value: str | None) -> str:
    return re.sub(r"\s+", "", value or "")


def _finding(code: str, target_type: str, target_id: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "target_type": target_type, "target_id": target_id, "message": message, **details}


def run_rule_checks(objects: dict[str, Any]) -> list[dict[str, Any]]:
    """Return blocking deterministic findings for the latest S1-S4 output."""

    findings: list[dict[str, Any]] = []
    evidence_by_id = {item.evidence_id: item for item in objects["evidence"]}
    interpretations = [objects["overall"], *objects["article_interpretations"]]

    for requirement in objects["requirements"]:
        source_text = _compact(requirement.source_text)
        article_text = _compact(requirement.article.original_text if requirement.article else "")
        if not source_text:
            continue
        if article_text and source_text not in article_text:
            findings.append(_finding(
                "REQUIREMENT_SOURCE_TEXT_MISMATCH",
                "requirement",
                requirement.requirement_id,
                "监管要求原文片段无法在对应条款原文中定位。",
            ))

        source_numbers = {item["original_expression"] for item in _extract_numbers(requirement.source_text)}
        structured_numbers: set[str] = set()
        for item in (requirement.structured_data or {}).get("numbers") or []:
            if isinstance(item, dict) and item.get("original_expression"):
                structured_numbers.add(str(item["original_expression"]))
        for expression in sorted(source_numbers - structured_numbers):
            findings.append(_finding(
                "NUMERIC_EXPRESSION_NOT_STRUCTURED",
                "requirement",
                requirement.requirement_id,
                f"原文中的结构化数字未进入监管要求字段：{expression}",
                expression=expression,
            ))

    for interpretation in interpretations:
        for block in interpretation.content_blocks or []:
            label = str(block.get("label") or "").upper()
            if label not in ALLOWED_BLOCK_LABELS:
                findings.append(_finding(
                    "CONTENT_BLOCK_LABEL_INVALID",
                    "interpretation",
                    interpretation.interpretation_id,
                    f"内容块标签不在允许集合内：{label or '空标签'}",
                    label=label,
                ))
            if not block.get("text") or not block.get("evidence_ids"):
                findings.append(_finding(
                    "CONTENT_BLOCK_EVIDENCE_INCOMPLETE",
                    "interpretation",
                    interpretation.interpretation_id,
                    "每个内容块都必须有文本和证据定位。",
                ))
            for evidence_id in block.get("evidence_ids") or []:
                if str(evidence_id) not in evidence_by_id:
                    findings.append(_finding(
                        "CONTENT_BLOCK_EVIDENCE_MISSING",
                        "interpretation",
                        interpretation.interpretation_id,
                        f"内容块引用了不存在的证据：{evidence_id}",
                        evidence_id=str(evidence_id),
                    ))

        interpretation_text = "\n".join(
            str(value or "")
            for value in (interpretation.summary, interpretation.interpretation, interpretation.regulatory_meaning)
        )
        interpretation_text += "\n" + "\n".join(
            str(block.get("text") or "")
            for block in interpretation.content_blocks or []
            if str(block.get("label") or "").upper() in {"INTERPRETATION", "CHANGE"}
        )
        for phrase in ABSOLUTE_LANGUAGE:
            if phrase in interpretation_text:
                findings.append(_finding(
                    "INTERPRETATION_ABSOLUTE_LANGUAGE",
                    "interpretation",
                    interpretation.interpretation_id,
                    f"解读包含需要人工确认的绝对化表述：{phrase}",
                    phrase=phrase,
                ))

    for evidence in objects["evidence"]:
        document = evidence.source_document
        locator_hash = (evidence.locator or {}).get("source_sha256") or (evidence.locator or {}).get("sha256")
        if locator_hash and document and document.sha256 and locator_hash != document.sha256:
            findings.append(_finding(
                "EVIDENCE_SOURCE_HASH_MISMATCH",
                "evidence",
                evidence.evidence_id,
                "证据定位记录的来源哈希与实际文件哈希不一致。",
                locator_sha256=locator_hash,
                source_sha256=document.sha256,
            ))

    return findings
