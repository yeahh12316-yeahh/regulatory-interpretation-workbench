"""Deterministic, evidence-first S4 interpretation builders.

This module only explains the registered regulatory text and S3 fields. S5
change rows are reported as facts; their regulatory meaning remains marked for
human review and is never expanded into an impact, gap, or remediation claim.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


_CHANGE_LABELS = {
    "ADDED": "新增条款",
    "DELETED": "删除条款",
    "MODIFIED": "修改条款",
}


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def _unique(values: list[str | None]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _requirement_point(requirement: Any) -> str:
    subject = getattr(requirement, "subject", None) or "相关主体"
    action = getattr(requirement, "action", None) or "关注"
    object_text = getattr(requirement, "object", None) or getattr(requirement, "source_text", "")[:80]
    point = f"{subject}{action}{object_text}"
    qualifiers = _unique([
        getattr(requirement, "condition", None),
        getattr(requirement, "deadline", None),
        getattr(requirement, "frequency", None),
        getattr(requirement, "threshold", None),
        getattr(requirement, "exception", None),
    ])
    return f"{point}（{'；'.join(qualifiers)}）" if qualifiers else point


def _change_map(s5_output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if s5_output.get("comparison_status") != "COMPLETED":
        return {}
    return {change.get("article_no"): change for change in s5_output.get("changes", []) if change.get("article_no")}


def _change_block(change: dict[str, Any], evidence_id: str) -> dict[str, Any]:
    change_type = change.get("change_type", "MODIFIED")
    dimensions = " / ".join(change.get("change_dimensions") or []) or "TEXT"
    label = _CHANGE_LABELS.get(change_type, change_type)
    old_text = (change.get("old_evidence") or {}).get("source_text") or "无旧规原文"
    new_text = (change.get("new_evidence") or {}).get("source_text") or "无新规原文"
    return {
        "label": "CHANGE",
        "text": f"S5识别为{label}，变化维度为：{dimensions}。旧规原文：{old_text} 新规原文：{new_text}。以上是可定位的文本或结构化变化事实，具体监管含义仍需人工复核。",
        "evidence_ids": [evidence_id],
        "s5_change_id": change.get("change_id"),
        "change_type": change_type,
        "change_dimensions": change.get("change_dimensions") or [],
        "old_evidence": change.get("old_evidence"),
        "new_evidence": change.get("new_evidence"),
    }


def _change_boundary_block(s5_output: dict[str, Any], evidence_ids: list[str]) -> dict[str, Any]:
    status = s5_output.get("comparison_status") or "NOT_RUN"
    reason = s5_output.get("reason") or "S5 尚未形成可核验的版本比较结果。"
    if status == "COMPLETED":
        counts = (s5_output.get("summary") or {}).get("counts") or {}
        text = (
            f"S5已识别新增{counts.get('ADDED', 0)}条、删除{counts.get('DELETED', 0)}条、修改{counts.get('MODIFIED', 0)}条。"
            "本段只报告有原文和定位支持的变化事实，不据此判断监管趋严、放宽、机构影响或整改要求。"
        )
        interpretation_status = "GENERATED_NEEDS_REVIEW"
    else:
        text = f"S5变化解读未生成。当前状态：{status}。{reason}"
        interpretation_status = "NOT_GENERATED"
    return {
        "label": "CHANGE",
        "text": text,
        "evidence_ids": evidence_ids,
        "s5_status": status,
        "interpretation_status": interpretation_status,
    }


def build_overall_fields(
    *,
    regulation: Any,
    version: Any,
    source_document: Any,
    articles: list[Any],
    requirements: list[Any],
    applicability: dict[str, Any],
    s5_output: dict[str, Any],
    evidence_ids: list[str],
) -> dict[str, Any]:
    points = [_requirement_point(item) for item in requirements[:6]]
    action_strength = Counter((item.structured_data or {}).get("action_strength_level") for item in requirements if getattr(item, "structured_data", None))
    s5_status = s5_output.get("comparison_status") or "NOT_RUN"
    interpretation = (
        f"本次解读基于已登记的《{regulation.title}》{version.version_label}原文，识别出 {len(articles)} 个条款和 {len(requirements)} 个结构化监管要求。"
        f"当前任务机构类型为“{applicability.get('institution_type') or '已登记机构类型'}”，适用性判断为“{applicability.get('status', 'NEEDS_REVIEW')}”。"
        "下述内容区分原文事实、登记信息和规则生成的初步解释，需经人工复核。"
    )
    key_points = points
    if s5_status == "COMPLETED":
        counts = (s5_output.get("summary") or {}).get("counts") or {}
        key_points = [*key_points, f"版本比较识别：新增{counts.get('ADDED', 0)}条、删除{counts.get('DELETED', 0)}条、修改{counts.get('MODIFIED', 0)}条。"]
    else:
        key_points = [*key_points, "旧规版本比较尚未形成可核验结果，未生成变化解读。"]
    fact_text = f"法规原文共 {len(articles)} 条，来源文件 {source_document.file_name}，共 {source_document.page_count or '未知'} 页；S3已结构化 {len(requirements)} 条监管要求。"
    official_text = (
        f"登记信息：发布机关为{'、'.join(regulation.issuer) or '待确认'}，文号为{regulation.document_no or '待确认'}，"
        f"发布日期为{_iso(getattr(version, 'publish_date', None)) or '待确认'}，生效日期为{_iso(getattr(version, 'effective_date', None)) or '待确认'}。"
    )
    interpretation_text = f"从已抽取的规范词和动作字段看，当前要求中强制性要求 {action_strength.get('must', 0)} 条、禁止性要求 {action_strength.get('must_not', 0) + action_strength.get('prohibited', 0)} 条；该统计用于辅助阅读，不替代逐条核验。"
    content_blocks = [
        {"label": "FACT", "text": fact_text, "evidence_ids": evidence_ids[:3]},
        {"label": "OFFICIAL", "text": official_text, "evidence_ids": evidence_ids[:3]},
        {"label": "INTERPRETATION", "text": interpretation_text, "evidence_ids": evidence_ids[:3]},
        _change_boundary_block(s5_output, evidence_ids[:3]),
    ]
    return {
        "summary": f"{regulation.title}已完成法规概览、适用性、S3监管要求和S5状态整理；当前结果需人工复核。",
        "interpretation": interpretation,
        "regulatory_meaning": "该整体解读仅说明已登记监管原文及其结构化字段，不扩展至内部制度、合规评价、整改或企业影响判断。",
        "key_points": key_points,
        "conditions": _unique([applicability.get("reason")]),
        "exceptions": [s5_output.get("reason") or "S5状态待确认。"],
        "content_blocks": content_blocks,
        "change_interpretation_status": "GENERATED_NEEDS_REVIEW" if s5_status == "COMPLETED" else "NOT_GENERATED",
        "change_count": len(s5_output.get("changes") or []) if s5_status == "COMPLETED" else 0,
    }


def build_article_fields(*, article: Any, requirements: list[Any], evidence_id: str, s5_output: dict[str, Any]) -> dict[str, Any]:
    points = [_requirement_point(item) for item in requirements]
    subject = requirements[0].subject if requirements and requirements[0].subject else "相关主体"
    actions = _unique([item.action for item in requirements])
    objects = _unique([item.object for item in requirements])
    conditions = _unique([item.condition for item in requirements])
    exceptions = _unique([item.exception for item in requirements])
    if requirements:
        interpretation = f"{article.article_no}的原文要求主体“{subject}”执行“{'、'.join(actions) or '相关事项'}”，对象集中在“{'、'.join(objects) or '原文所述事项'}”。"
        if conditions:
            interpretation += f"适用条件包括：{'；'.join(conditions)}。"
        if exceptions:
            interpretation += f"原文例外包括：{'；'.join(exceptions)}。"
        interpretation += "具体监管含义仍需人工复核。"
    else:
        interpretation = f"{article.article_no}暂未从当前原文中识别出明确的行为义务，不能据此扩展监管要求，需人工复核。"
    change = _change_map(s5_output).get(article.article_no)
    blocks = [
        {"label": "FACT", "text": article.original_text, "evidence_ids": [evidence_id]},
        {"label": "OFFICIAL", "text": f"证据定位：第 {article.source_page or '待确认'} 页，{article.article_no}。", "evidence_ids": [evidence_id]},
        {"label": "INTERPRETATION", "text": interpretation, "evidence_ids": [evidence_id]},
    ]
    if change:
        blocks.append(_change_block(change, evidence_id))
        change_status = "GENERATED_NEEDS_REVIEW"
    elif s5_output.get("comparison_status") == "COMPLETED":
        change_status = "NO_CHANGE_IDENTIFIED"
    else:
        change_status = "NOT_GENERATED"
    return {
        "summary": f"{article.article_no}：{points[0] if points else '原文已载入，暂未识别出明确行为义务。'}",
        "interpretation": interpretation,
        "regulatory_meaning": "该条解读仅对已登记原文和S3结构化要求进行说明，不替代正式法律意见。",
        "key_points": points,
        "conditions": conditions,
        "exceptions": exceptions,
        "content_blocks": blocks,
        "change_interpretation_status": change_status,
        "change_id": change.get("change_id") if change else None,
    }
