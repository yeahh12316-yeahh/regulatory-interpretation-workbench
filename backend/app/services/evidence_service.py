"""Validation helpers for the Regulation -> Evidence chain."""

from __future__ import annotations

from typing import Any


def _linked_ids(interpretation: Any) -> set[str]:
    ids = {evidence.evidence_id for evidence in interpretation.evidence}
    for block in interpretation.content_blocks or []:
        ids.update(str(value) for value in block.get("evidence_ids") or [])
    return ids


def validate_evidence_chain(objects: dict[str, Any]) -> list[dict[str, Any]]:
    """Return explicit chain findings without changing review state."""

    evidence_by_id = {item.evidence_id: item for item in objects["evidence"]}
    findings: list[dict[str, Any]] = []
    for interpretation in [objects["overall"], *objects["article_interpretations"]]:
        linked_ids = _linked_ids(interpretation)
        if not linked_ids:
            findings.append({"code": "INTERPRETATION_EVIDENCE_MISSING", "target_id": interpretation.interpretation_id, "message": "解读没有绑定证据。"})
        for evidence_id in sorted(linked_ids):
            if evidence_id not in evidence_by_id:
                findings.append({"code": "EVIDENCE_REFERENCE_MISSING", "target_id": interpretation.interpretation_id, "evidence_id": evidence_id, "message": "内容块引用的证据不存在于当前任务证据集中。"})

    for requirement in objects["requirements"]:
        if not requirement.evidence:
            findings.append({"code": "REQUIREMENT_EVIDENCE_MISSING", "target_id": requirement.requirement_id, "message": "监管要求没有绑定证据。"})

    for evidence in objects["evidence"]:
        locator = evidence.locator or {}
        missing = []
        if not evidence.source_document_id:
            missing.append("source_document_id")
        if not locator.get("sha256"):
            missing.append("sha256")
        if locator.get("page") is None:
            missing.append("page")
        if not (evidence.source_text or "").strip():
            missing.append("source_text")
        if missing:
            findings.append({"code": "EVIDENCE_LOCATOR_INCOMPLETE", "target_id": evidence.evidence_id, "missing": missing, "message": f"证据定位字段不完整：{'、'.join(missing)}。"})
    return findings


def evidence_link_payload(evidence: Any) -> dict[str, Any]:
    locator = dict(evidence.locator or {})
    return {
        "evidence_id": evidence.evidence_id,
        "source_document_id": evidence.source_document_id,
        "source_type": evidence.source_type,
        "source_text": evidence.source_text,
        "description": evidence.description,
        "verification_status": evidence.verification_status,
        "locator": locator,
        "page": locator.get("page"),
        "article_no": locator.get("article_no"),
        "source_offset": {key: value for key, value in locator.items() if key in {"start", "end", "line_start", "line_end", "char_start", "char_end", "extraction_method"}},
        "source_hash": locator.get("sha256"),
    }
