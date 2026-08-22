"""Evidence-first S5 comparison of two verified regulation versions."""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter
from typing import Any


_SCOPE_TERMS = ("适用于", "仅适用于", "金融企业", "金融机构", "商业银行", "境内", "全国")
_TIME_TERMS = ("施行", "生效", "废止", "停止执行", "过渡期", "自", "起", "以内", "内", "前", "后")
_THRESHOLD_TERMS = ("以上", "以下", "不超过", "不得低于", "不低于", "超过", "少于", "不少于", "以内")
_NORMATIVE_TERMS = ("应当", "必须", "不得", "禁止", "严禁", "可以", "可", "宜")


def _normalise_text(value: str | None) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or ""))


def _source_payload(version: Any, article: Any | None) -> dict[str, Any] | None:
    if article is None:
        return None
    source_document = getattr(version, "source_document", None)
    source_document_id = getattr(version, "source_document_id", None) or getattr(source_document, "document_id", None)
    source_hash = getattr(version, "source_sha256", None) or getattr(source_document, "sha256", None)
    return {
        "version_id": getattr(version, "version_id", None),
        "version_label": getattr(version, "version_label", None),
        "source_document_id": source_document_id,
        "source_file_name": getattr(source_document, "file_name", None),
        "source_hash": source_hash,
        "article_id": getattr(article, "article_id", None),
        "article_no": getattr(article, "article_no", None),
        "page": getattr(article, "source_page", None),
        "source_offset": getattr(article, "source_offset", None) or {},
        "source_text": getattr(article, "original_text", ""),
    }


def _numeric_signature(text: str) -> list[tuple[str, str]]:
    # Import lazily to keep the comparison service independent of the S1-S4
    # pipeline module during application startup.
    from backend.app.services.interpretation_pipeline import _extract_numbers

    return [(item.get("numeric_type", "other"), item.get("normalized_value", "")) for item in _extract_numbers(text)]


def _terms(text: str, candidates: tuple[str, ...]) -> set[str]:
    return {term for term in candidates if term in text}


def _change_dimensions(old_text: str, new_text: str) -> list[str]:
    dimensions: list[str] = []
    if _normalise_text(old_text) != _normalise_text(new_text):
        dimensions.append("TEXT")
    if _numeric_signature(old_text) != _numeric_signature(new_text):
        dimensions.append("NUMERIC")
    if _terms(old_text, _SCOPE_TERMS) != _terms(new_text, _SCOPE_TERMS):
        dimensions.append("SCOPE")
    if _terms(old_text, _TIME_TERMS) != _terms(new_text, _TIME_TERMS):
        dimensions.append("TIME")
    if _terms(old_text, _THRESHOLD_TERMS) != _terms(new_text, _THRESHOLD_TERMS):
        dimensions.append("THRESHOLD")
    if _terms(old_text, _NORMATIVE_TERMS) != _terms(new_text, _NORMATIVE_TERMS):
        dimensions.append("NORMATIVE_STRENGTH")
    return list(dict.fromkeys(dimensions))


def _compact_diff(old_text: str, new_text: str) -> list[dict[str, str]]:
    matcher = difflib.SequenceMatcher(a=_normalise_text(old_text), b=_normalise_text(new_text), autojunk=False)
    output: list[dict[str, str]] = []
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        item: dict[str, str] = {"operation": tag}
        if old_start != old_end:
            item["old_text"] = _normalise_text(old_text)[old_start:old_end][:300]
        if new_start != new_end:
            item["new_text"] = _normalise_text(new_text)[new_start:new_end][:300]
        output.append(item)
    return output[:30]


def _version_metadata(version: Any) -> dict[str, Any]:
    source_document = getattr(version, "source_document", None)
    return {
        "version_id": getattr(version, "version_id", None),
        "version_label": getattr(version, "version_label", None),
        "publish_date": getattr(getattr(version, "publish_date", None), "isoformat", lambda: None)(),
        "effective_date": getattr(getattr(version, "effective_date", None), "isoformat", lambda: None)(),
        "source_document_id": getattr(version, "source_document_id", None) or getattr(source_document, "document_id", None),
        "source_file_name": getattr(source_document, "file_name", None),
        "source_hash": getattr(version, "source_sha256", None) or getattr(source_document, "sha256", None),
        "article_count": len(getattr(version, "articles", None) or []),
    }


def _blocked(status: str, reason: str, required_inputs: list[str], current: Any, previous: Any | None = None) -> dict[str, Any]:
    return {
        "stage_status": "skipped" if status == "SKIPPED_NO_PREVIOUS_SOURCE" else "blocked",
        "output": {
            "comparison_status": status,
            "reason": reason,
            "required_inputs": required_inputs,
            "changes": [],
            "summary": {"counts": {"ADDED": 0, "DELETED": 0, "MODIFIED": 0}, "old_article_count": len(getattr(previous, "articles", None) or []) if previous else 0, "new_article_count": len(getattr(current, "articles", None) or [])},
            "old_version": _version_metadata(previous) if previous else None,
            "new_version": _version_metadata(current),
            "interpretation_status": "NOT_GENERATED",
        },
    }


def compare_regulation_versions(current_version: Any, previous_version: Any | None, *, relation_confirmed: bool) -> dict[str, Any]:
    """Compare article text only after the old source and relation pass the gate.

    The service intentionally returns no change rows for every non-ready state.
    S5 identifies textual/regulatory dimensions; S4 remains responsible for any
    later human-reviewed interpretation of what a change means.
    """

    if previous_version is None:
        return _blocked(
            "SKIPPED_NO_PREVIOUS_SOURCE",
            "未登记可核验的旧版法规原文，S5 不生成差异结论。",
            ["old_source_document", "verified_version_relation", "old_source_sha256"],
            current_version,
        )
    if not relation_confirmed:
        return _blocked(
            "WAITING_RELATION_CONFIRMATION",
            "数据库存在前一版本，但版本关系尚未由有权人员确认，S5 暂不生成差异结论。",
            ["verified_version_relation"],
            current_version,
            previous_version,
        )

    old_articles = list(getattr(previous_version, "articles", None) or [])
    new_articles = list(getattr(current_version, "articles", None) or [])
    missing_inputs: list[str] = []
    for label, version in (("old", previous_version), ("new", current_version)):
        source_document = getattr(version, "source_document", None)
        if not getattr(version, "source_document_id", None) and not getattr(source_document, "document_id", None):
            missing_inputs.append(f"{label}_source_document")
        if not getattr(version, "source_sha256", None) and not getattr(source_document, "sha256", None):
            missing_inputs.append(f"{label}_source_sha256")
        version_hash = getattr(version, "source_sha256", None)
        document_hash = getattr(source_document, "sha256", None)
        if version_hash and document_hash and version_hash != document_hash:
            missing_inputs.append(f"{label}_source_hash_mismatch")
        if not getattr(version, "articles", None):
            missing_inputs.append(f"{label}_articles")
    if missing_inputs:
        return _blocked("WAITING_SOURCE_VERIFICATION", "两份版本的原文、哈希或条款结构尚未完整登记。", missing_inputs, current_version, previous_version)

    old_by_no = {article.article_no: article for article in old_articles}
    new_by_no = {article.article_no: article for article in new_articles}
    changes: list[dict[str, Any]] = []
    unchanged_count = 0
    for article_no in sorted(set(old_by_no) | set(new_by_no), key=lambda value: (len(value), value)):
        old_article = old_by_no.get(article_no)
        new_article = new_by_no.get(article_no)
        old_text = getattr(old_article, "original_text", "") if old_article else ""
        new_text = getattr(new_article, "original_text", "") if new_article else ""
        if old_article and new_article:
            if _normalise_text(old_text) == _normalise_text(new_text):
                unchanged_count += 1
                continue
            change_type = "MODIFIED"
            dimensions = _change_dimensions(old_text, new_text)
        elif new_article:
            change_type = "ADDED"
            dimensions = ["ARTICLE_ADDED"]
        else:
            change_type = "DELETED"
            dimensions = ["ARTICLE_DELETED"]
        changes.append(
            {
                "change_id": f"S5-{change_type}-{article_no}",
                "article_no": article_no,
                "change_type": change_type,
                "change_dimensions": dimensions,
                "old_evidence": _source_payload(previous_version, old_article),
                "new_evidence": _source_payload(current_version, new_article),
                "text_diff": _compact_diff(old_text, new_text) if old_article and new_article else [],
                "interpretation_status": "NOT_GENERATED_S4_BOUNDARY",
            }
        )
    counts = Counter(item["change_type"] for item in changes)
    output = {
        "comparison_status": "COMPLETED",
        "reason": "两份原文、文件哈希和版本关系已确认，已完成条款级文本与结构化数字比较。",
        "old_version": _version_metadata(previous_version),
        "new_version": _version_metadata(current_version),
        "summary": {
            "counts": {name: counts.get(name, 0) for name in ("ADDED", "DELETED", "MODIFIED")},
            "old_article_count": len(old_articles),
            "new_article_count": len(new_articles),
            "changed_article_count": len(changes),
        },
        "unchanged_article_count": unchanged_count,
        "changes": changes,
        "interpretation_status": "NOT_GENERATED_S4_BOUNDARY",
        "interpretation_note": "S5 只识别可定位的版本差异；变化的监管含义需进入 S4/人工复核，不自动扩展为内部制度或整改结论。",
        "required_inputs": [],
    }
    return {"stage_status": "completed", "output": output}
