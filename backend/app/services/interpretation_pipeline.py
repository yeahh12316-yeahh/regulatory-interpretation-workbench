"""Evidence-first S1-S4 regulatory interpretation pipeline.

The first production slice intentionally uses deterministic extraction and
templated interpretation. It is executable without a model key, preserves the
source text verbatim, and marks every generated result for human review. A
model provider can be introduced behind the same result contract later without
changing the evidence or database boundary.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Article, Evidence, Interpretation, RegulationVersion, Requirement, Task
from backend.app.services.interpretation_s4 import build_article_fields, build_overall_fields
from backend.app.services.regulation_ingest import DOCUMENT_NO_PATTERN, VERSION_PATTERN


PIPELINE_VERSION = "s1-s4-rule-based-v1"
_MODAL_RULES = (
    ("不得", "PROHIBITION"),
    ("禁止", "PROHIBITION"),
    ("严禁", "PROHIBITION"),
    ("应当", "OBLIGATION"),
    ("必须", "OBLIGATION"),
    ("须", "OBLIGATION"),
    ("应", "OBLIGATION"),
    ("可以", "PERMISSION"),
    ("可", "PERMISSION"),
    ("有权", "PERMISSION"),
    ("要", "OBLIGATION"),
    ("是指", "DEFINITION"),
)
_NUMERIC_PATTERN = re.compile(
    rf"(?P<document_no>{DOCUMENT_NO_PATTERN.pattern})|"
    r"(?P<date>20\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日(?:起|之日起)?)|"
    r"(?P<amount>\d+(?:\.\d+)?\s*(?:亿元|万元|元))|"
    r"(?P<percentage>\d+(?:\.\d+)?\s*[%％])|"
    r"(?P<duration>\d+(?:\.\d+)?\s*(?:年|个月|月|日|天|小时)(?:以上|以下|以内|内|起|后|前)?(?!版|修订版))|"
    r"(?P<reference>附\s*[一二三四五六七八九十百千万0-9]+)"
)
_TIME_PATTERN = re.compile(r"(?:\d+(?:\.\d+)?|[一二三四五六七八九十百千万零〇]+)(?:年|个月|月|日|天|小时)(?:以上|以下|内|以内|起|后|前)?")
_FREQUENCY_PATTERN = re.compile(r"(?:每(?:年|月|季度|日)|定期|不定期|及时|持续|按期|至少每[^，。；]{0,12})")
_NORMATIVE_TERMS = tuple(dict.fromkeys([term for term, _ in _MODAL_RULES] + ["宜", "不应", "严禁", "禁止", "按规定", "参照执行", "负责", "及时"]))
_ACTION_VERBS = ("建立", "健全", "完善", "履行", "报送", "报告", "出具", "发现", "实现", "维护", "加强", "分析", "形成", "做好", "制定", "进行", "明确", "实行", "承担", "完成", "采取", "实施", "提供", "获取", "审计", "追究", "审批", "施行", "废止", "生效", "替代", "取代", "修订")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[。；;])", text) if part.strip()]


def _first_modal(text: str) -> tuple[int, str, str] | None:
    matches = [(text.find(keyword), keyword, rule_type) for keyword, rule_type in _MODAL_RULES if text.find(keyword) >= 0]
    if not matches:
        return None
    return min(matches, key=lambda item: (item[0], -len(item[1])))


def _normative_terms(text: str) -> list[str]:
    return [term for term in _NORMATIVE_TERMS if term in text]


def _action_strength_level(action: str | None) -> str | None:
    if action in {"不得", "不应"}:
        return "must_not"
    if action in {"严禁", "禁止"}:
        return "prohibited"
    if action in {"应当", "必须", "须", "要", "负责"}:
        return "must"
    if action in {"应", "宜"}:
        return "should"
    if action in {"可以", "可", "有权"}:
        return "permission"
    return None


def _action_category(action: str | None, object_text: str | None) -> str | None:
    value = f"{action or ''}{object_text or ''}"
    if action in {"不得", "不应", "严禁", "禁止"}:
        return "禁止类"
    if any(keyword in value for keyword in ("报送", "报告", "出具", "披露")):
        return "报告类"
    if any(keyword in value for keyword in ("明确", "约定")):
        return "约定类"
    if any(keyword in value for keyword in ("审计", "审查", "审核", "审议", "检查", "评价")):
        return "评估类"
    if any(keyword in value for keyword in ("建立", "健全", "完善", "制定", "构建")):
        return "建设类"
    if action is None:
        return None
    return "执行类"


def _extract_conditions(text: str) -> list[str]:
    candidates = re.findall(r"(?:在|如|当|根据|按照|依照|依据|经|符合|对于|除|无法)[^，。；]{1,80}", text)
    return list(dict.fromkeys(candidate.strip() for candidate in candidates))


def _extract_exceptions(text: str) -> list[str]:
    candidates = re.findall(r"(?:除|但)[^，。；]{1,80}(?:外|除外|情形)", text)
    return list(dict.fromkeys(candidate.strip() for candidate in candidates))


def _extract_cross_references(text: str) -> list[str]:
    candidates = re.findall(r"(?:根据|按照|依照|依据|参照|按规定|参照执行)[^，。；]{0,80}|《[^》]+》|附[一二三四五六七八九十百千万0-9]+", text)
    return list(dict.fromkeys(candidate.strip() for candidate in candidates))


def _extract_numbers(text: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for match in _NUMERIC_PATTERN.finditer(text):
        raw_expression = match.group(0)
        expression = re.sub(r"\s+", "", raw_expression)
        numeric_type = match.lastgroup or "other"
        if numeric_type == "document_no":
            numeric_type = "document_number"
        elif numeric_type == "date":
            numeric_type = "date"
        elif numeric_type == "reference":
            numeric_type = "reference"
        normalized_value: float | str | None = None
        if numeric_type in {"duration", "percentage", "amount"}:
            number_match = re.search(r"\d+(?:\.\d+)?", expression)
            normalized_value = float(number_match.group(0)) if number_match else None
        elif numeric_type == "date":
            normalized_value = expression.replace("年", "-").replace("月", "-").replace("日", "").replace("之日起", "").replace("起", "")
        elif numeric_type in {"document_number", "reference"}:
            normalized_value = expression
        values.append(
            {
                "original_expression": expression,
                "numeric_type": numeric_type,
                "normalized_value": normalized_value,
                "start": match.start(),
                "end": match.end(),
                "context": text[max(0, match.start() - 24) : min(len(text), match.end() + 24)],
            }
        )
    return values


def _split_compound_segment(segment: str) -> list[str]:
    modal_positions = [match.start() for term, _ in _MODAL_RULES for match in re.finditer(re.escape(term), segment)]
    modal_positions = sorted(set(modal_positions))
    first_modal = _first_modal(segment)
    verb_positions = [match.start() for verb in _ACTION_VERBS for match in re.finditer(re.escape(verb), segment)]
    verb_positions = sorted(set(verb_positions))
    first_verb = next((position for position in verb_positions if not first_modal or position > first_modal[0] + len(first_modal[1])), None)
    split_candidates = modal_positions[1:]
    if first_verb is not None:
        split_candidates.extend(position for position in verb_positions if position > first_verb)
    split_candidates = sorted(set(split_candidates))
    if not split_candidates:
        return [segment.strip()]
    chunks: list[str] = []
    start = 0
    for position in split_candidates:
        separator = max(segment.rfind("，", start, position), segment.rfind(",", start, position))
        prefix = segment[start:separator] if separator >= start else ""
        if separator > start and _first_modal(prefix) is not None:
            chunks.append(segment[start:separator].strip(" ，,"))
            start = separator + 1
    chunks.append(segment[start:].strip(" ，,"))
    return [chunk for chunk in chunks if chunk]


def _extract_requirement(article: Article, segment: str, index: int, *, subject_hint: str | None = None) -> dict[str, Any]:
    modal = _first_modal(segment)
    if modal is None:
        explicit_action = next((verb for verb in _ACTION_VERBS if verb in segment), None)
        rule_type = "SCOPE" if any(keyword in segment for keyword in ("适用", "适用于", "范围")) else ("OBLIGATION" if explicit_action else "OTHER")
        subject = subject_hint or "本条规定的责任主体"
        action = explicit_action
        object_text = segment[segment.find(explicit_action) + len(explicit_action) :].strip(" ：:，,。；;") if explicit_action else segment
    else:
        position, keyword, rule_type = modal
        before = re.split(r"[，。；;]", segment[:position])[-1].strip()
        subject = before[-80:] if before and before not in {"并", "且", "并且", "同时"} else (subject_hint or "本条规定的责任主体")
        action_text = segment[position + len(keyword):].strip(" ：:，,。；;")
        action = keyword
        object_text = action_text[:240] or None

    numbers = _extract_numbers(segment)
    deadline_match = _TIME_PATTERN.search(segment)
    frequency_match = _FREQUENCY_PATTERN.search(segment)
    threshold = None
    if any(token in segment for token in ("至少", "不超过", "不少于", "不低于", "超过", "%", "％")):
        threshold = segment[:300]
    normative_terms = _normative_terms(segment)
    exceptions = _extract_exceptions(segment)
    cross_references = _extract_cross_references(segment)
    strength_level = _action_strength_level(action)
    action_category = _action_category(action, object_text)

    return {
        "requirement_id": f"REQ_{article.article_id}_{index:03d}",
        "article_id": article.article_id,
        "subject": subject,
        "rule_type": rule_type,
        "action": action,
        "object": object_text,
        "condition": "；".join(_extract_conditions(segment)) or None,
        "deadline": deadline_match.group(0) if deadline_match else None,
        "frequency": frequency_match.group(0) if frequency_match else None,
        "threshold": threshold,
        "exception": "；".join(exceptions) or None,
        "evidence_required": None,
        "related_articles": [],
        "source_text": segment,
        "confidence": 0.86 if modal else 0.62,
        "fact_class": "FACT",
        "review_status": "needs_review",
        "structured_data": {
            "modal_keyword": modal[1] if modal else None,
            "numbers": numbers,
            "conditions": _extract_conditions(segment),
            "exceptions": exceptions,
            "normative_terms": normative_terms,
            "action_strength": action,
            "action_strength_level": strength_level,
            "action_category": action_category,
            "cross_references": cross_references,
            "frequency_category": "定期频次" if frequency_match and any(keyword in frequency_match.group(0) for keyword in ("每", "定期", "不定期")) else ("事件触发型" if frequency_match else None),
            "transitional_period": next((number["original_expression"] for number in numbers if number["numeric_type"] in {"date", "duration"} and any(keyword in segment for keyword in ("施行", "生效", "过渡"))), None),
            "plain_text_summary": f"{subject}{action or '涉及'}{object_text or ''}"[:120],
        },
    }


def extract_requirements(article: Article) -> list[dict[str, Any]]:
    segments = _split_sentences(article.original_text)
    extracted: list[dict[str, Any]] = []
    for segment in segments:
        if _first_modal(segment) or any(keyword in segment for keyword in ("适用于", "适用范围", "定义", "不得", "应当", "必须", "参照执行", "负责", "施行", "废止", "生效", "替代", "取代")):
            subject_hint = None
            first_modal = _first_modal(segment)
            if first_modal:
                subject_hint = segment[: first_modal[0]].strip(" ，,：:") or None
            for atomic_segment in _split_compound_segment(segment):
                extracted.append(_extract_requirement(article, atomic_segment, len(extracted) + 1, subject_hint=subject_hint))
    return extracted


def evaluate_applicability(
    regulation_title: str,
    article_text: str,
    institution_type: str,
    region: str | None,
    *,
    business_scope: list[str] | None = None,
    effective_date: date | None = None,
    abolish_date: date | None = None,
    interpretation_as_of: str | None = None,
) -> dict[str, Any]:
    text = f"{regulation_title}\n{article_text}"
    business_scope = [item.strip() for item in (business_scope or []) if item and item.strip()]
    institution_match = bool(institution_type and (institution_type in text or "金融企业" in text or "金融机构" in text))
    explicit_scope = any(keyword in text for keyword in ("适用于", "适用范围", "金融企业", "金融机构", "商业银行"))
    business_match: bool | None = None if not business_scope else any(scope in text for scope in business_scope)
    has_region_boundary = any(keyword in text for keyword in ("境内", "境外", "全国", "中华人民共和国", "试点地区", "试点城市"))
    regional_match = True if not region or not has_region_boundary else bool(region in text or any(keyword in text for keyword in ("境内", "全国", "中华人民共和国")))
    temporal_match = True
    temporal_reason = "未提供解读时点，暂未发现时点冲突。"
    as_of_date: date | None = None
    if interpretation_as_of:
        try:
            as_of_date = date.fromisoformat(interpretation_as_of)
        except ValueError:
            temporal_match = False
            temporal_reason = "解读时点格式无法核验，需人工确认。"
    if as_of_date and effective_date and as_of_date < effective_date:
        temporal_match = False
        temporal_reason = f"解读时点早于生效日期 {effective_date.isoformat()}。"
    if as_of_date and abolish_date and as_of_date >= abolish_date:
        temporal_match = False
        temporal_reason = f"解读时点不早于废止日期 {abolish_date.isoformat()}。"

    exclusive_match = re.search(r"(?:仅|只)适用于([^。；;\n]{1,100})", text)
    explicit_exclusion = re.search(r"不适用于([^。；;\n]{1,100})", text)
    if exclusive_match and institution_type not in exclusive_match.group(1) and "金融企业" not in exclusive_match.group(1) and "金融机构" not in exclusive_match.group(1):
        status = "NOT_APPLICABLE"
        confidence = "high"
        reason = f"原文明确限定为“{exclusive_match.group(1).strip()}”，与当前机构类型“{institution_type}”不匹配。"
    elif explicit_exclusion and institution_type in explicit_exclusion.group(1):
        status = "NOT_APPLICABLE"
        confidence = "high"
        reason = f"原文明确写明不适用于当前机构类型“{institution_type}”。"
    elif not explicit_scope:
        status = "NEEDS_REVIEW"
        confidence = "low"
        reason = "原文未提供足够的机构类型或适用范围表述，不能直接承诺适用或不适用。"
    elif institution_match and business_match is True and regional_match and temporal_match:
        status = "DIRECTLY_APPLICABLE"
        confidence = "high"
        reason = f"原文适用范围与当前机构类型“{institution_type}”及业务范围存在直接匹配，地域和时点未发现冲突。"
    elif institution_match and not regional_match:
        status = "NEEDS_REVIEW"
        confidence = "low"
        reason = f"机构类型与原文存在匹配，但当前地域“{region}”与原文地域边界未能确认。"
    elif institution_match and not temporal_match:
        status = "NEEDS_REVIEW"
        confidence = "low"
        reason = temporal_reason
    elif institution_match and (business_match is False or business_match is None):
        status = "POTENTIALLY_APPLICABLE"
        confidence = "medium"
        reason = f"机构类型“{institution_type}”与原文存在匹配，但业务范围尚未形成直接匹配，暂列潜在适用。"
    elif explicit_scope and not institution_match:
        status = "NEEDS_REVIEW"
        confidence = "low"
        reason = f"原文存在适用范围线索，但无法将其与“{institution_type}”直接匹配。"
    else:
        status = "NEEDS_REVIEW"
        confidence = "low"
        reason = "原文未提供足够的机构类型、业务或地域边界，不能直接承诺适用或不适用。"
    return {
        "status": status,
        "confidence": confidence,
        "institution_type": institution_type,
        "business_scope": business_scope,
        "region": region,
        "interpretation_as_of": interpretation_as_of,
        "matching_stage": {
            "institution_type_match": institution_match,
            "business_scope_match": business_match,
            "regional_temporal_match": regional_match,
            "temporal_match": temporal_match,
        },
        "scope_signals": {
            "explicit_scope": explicit_scope,
            "exclusive_scope_text": exclusive_match.group(0).strip() if exclusive_match else None,
            "exclusion_text": explicit_exclusion.group(0).strip() if explicit_exclusion else None,
            "temporal_reason": temporal_reason,
        },
        "reason": reason,
        "evidence_required": True,
        "decision_basis": "REGULATION_TEXT_ONLY",
    }


def _scope_evidence(
    articles: list[Article],
    *,
    source_document_id: str,
    keywords: list[str],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for article in articles:
        matched = [keyword for keyword in keywords if keyword and keyword in article.original_text]
        if not matched:
            continue
        evidence.append(
            {
                "source_document_id": source_document_id,
                "article_id": article.article_id,
                "article_no": article.article_no,
                "page": article.source_page,
                "matched_terms": matched,
                "source_text": article.original_text[:500],
            }
        )
    return evidence[:8]


def _regulation_locator(version: RegulationVersion, *, s1_output: dict[str, Any]) -> dict[str, Any]:
    source_document = version.source_document
    metadata = source_document.document_metadata or {}
    extraction_summary = metadata.get("extraction_summary") if isinstance(metadata, dict) else {}
    extraction_summary = extraction_summary if isinstance(extraction_summary, dict) else {}
    metadata_fields = dict(s1_output.get("metadata_fields") or {})
    unresolved = list(s1_output.get("unresolved_fields") or [])
    identity_status = "IDENTIFIED" if not unresolved else "IDENTIFIED_WITH_REVIEW_REQUIRED"
    return {
        "status": identity_status,
        "regulation_id": version.regulation_id,
        "version_id": version.version_id,
        "title": version.regulation.title,
        "version_label": version.version_label,
        "document_no": version.regulation.document_no,
        "issuer": version.regulation.issuer,
        "publish_date": version.publish_date.isoformat() if version.publish_date else None,
        "effective_date": version.effective_date.isoformat() if version.effective_date else None,
        "source_document_id": source_document.document_id,
        "source_file_name": source_document.file_name,
        "source_hash": source_document.sha256,
        "source_type": source_document.source_type,
        "source_url": source_document.source_url,
        "page_count": source_document.page_count,
        "parse_status": metadata.get("parse_status") if isinstance(metadata, dict) else None,
        "warnings": list(metadata.get("warnings") or []) if isinstance(metadata, dict) else [],
        "extraction_summary": extraction_summary,
        "unresolved_fields": unresolved,
        "fields": metadata_fields,
        "identity_basis": "REGISTERED_SOURCE_DOCUMENT_AND_REGULATION_VERSION",
    }


def _version_relation(version: RegulationVersion, all_text: str, *, source_document_id: str) -> dict[str, Any]:
    current_document_no = version.regulation.document_no
    referenced_document_numbers = list(
        dict.fromkeys(
            re.sub(r"^(?:同时)?(?:废止|替代|取代|修订)", "", match.group(1)).replace(" ", "")
            for match in DOCUMENT_NO_PATTERN.finditer(all_text)
        )
    )
    candidates = [value for value in referenced_document_numbers if value != current_document_no]
    referenced_versions = list(dict.fromkeys(VERSION_PATTERN.findall(all_text)))
    relation_terms = [term for term in ("废止", "替代", "修订", "取代") if term in all_text]
    if version.previous_version_id:
        return {
            "status": "IDENTIFIED",
            "relation_type": "DIRECT_PREVIOUS_VERSION_REGISTERED",
            "from_version_id": version.previous_version_id,
            "to_version_id": version.version_id,
            "candidate_previous_document_numbers": candidates,
            "candidate_previous_versions": referenced_versions,
            "relation_terms": relation_terms,
            "source_document_id": source_document_id,
            "evidence_required": True,
            "reason": "数据库已登记当前版本的直接前一版本；进入 S5 前仍需核验两份原文和文件哈希。",
        }
    if candidates or referenced_versions or relation_terms:
        return {
            "status": "CANDIDATE_NEEDS_VERIFICATION",
            "relation_type": "POSSIBLE_PREVIOUS_VERSION_REFERENCED_IN_TEXT",
            "from_version_id": None,
            "to_version_id": version.version_id,
            "candidate_previous_document_numbers": candidates,
            "candidate_previous_versions": referenced_versions,
            "relation_terms": relation_terms,
            "source_document_id": source_document_id,
            "evidence_required": True,
            "reason": "当前原文提及其他版本或废止/替代关系，但旧版本原文尚未登记，不能将线索当成已核验版本关系。",
        }
    return {
        "status": "NO_REGISTERED_PREVIOUS",
        "relation_type": "NO_PREVIOUS_VERSION_REGISTERED",
        "from_version_id": None,
        "to_version_id": version.version_id,
        "candidate_previous_document_numbers": [],
        "candidate_previous_versions": [],
        "relation_terms": [],
        "source_document_id": source_document_id,
        "evidence_required": True,
        "reason": "当前任务只有一份已登记法规版本，未发现可直接确认的前一版本。",
    }


def _stage(status: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, "version": 1, **extra}


_S1_REQUIRED_METADATA_FIELDS = ("document_no", "issuer", "publish_date", "effective_date")


def _extraction_context(source_document: Any) -> tuple[str, str | None]:
    metadata = source_document.document_metadata or {}
    summary = metadata.get("extraction_summary") if isinstance(metadata, dict) else {}
    summary = summary if isinstance(summary, dict) else {}
    ocr_pages = summary.get("ocr_pages") or []
    pypdf_pages = summary.get("pypdf_pages") or []
    if ocr_pages:
        return "ocr", str(ocr_pages[0])
    if pypdf_pages:
        return "pypdf", str(pypdf_pages[0])
    return "unknown", None


def _metadata_field(
    *,
    name: str,
    value: Any,
    source_document: Any,
    manual_override: dict[str, Any] | None,
) -> dict[str, Any]:
    extraction_method, source_page = _extraction_context(source_document)
    if manual_override is not None:
        return {
            "value": manual_override.get("value"),
            "machine_value": manual_override.get("machine_value"),
            "status": "manual_verified",
            "confidence": "high",
            "extraction_method": "manual",
            "source_document_id": source_document.document_id,
            "source_locator": {"page": source_page, "section": "metadata", "reviewed": True},
            "reviewed_by": manual_override.get("reviewed_by"),
            "reviewed_at": manual_override.get("reviewed_at"),
        }
    if value is None or value == [] or value == "":
        status = "missing"
        confidence = "low"
    elif extraction_method == "ocr":
        status = "needs_review"
        confidence = "low"
    else:
        status = "machine_extracted"
        confidence = "medium" if extraction_method == "pypdf" else "low"
    return {
        "value": value,
        "machine_value": value,
        "status": status,
        "confidence": confidence,
        "extraction_method": extraction_method,
        "source_document_id": source_document.document_id,
        "source_locator": {"page": source_page, "section": "metadata"},
    }


def _metadata_unresolved(metadata_fields: dict[str, dict[str, Any]]) -> list[str]:
    return [name for name in _S1_REQUIRED_METADATA_FIELDS if not metadata_fields[name].get("value")]


def run_s1_s4_pipeline(
    db: Session,
    task: Task,
    *,
    institution_type: str,
    business_scope: list[str] | None = None,
    region: str | None = "中国境内",
    interpretation_as_of: str | None = None,
    progress_callback: Callable[[str, str, dict[str, Any] | None], None] | None = None,
) -> dict[str, Any]:
    if not task.regulation_id:
        raise ValueError("任务尚未绑定法规")
    version = db.scalar(
        select(RegulationVersion)
        .where(RegulationVersion.regulation_id == task.regulation_id, RegulationVersion.is_current.is_(True))
        .order_by(RegulationVersion.created_at.desc())
    )
    if version is None:
        raise ValueError("任务尚未登记当前法规版本")
    articles = list(db.scalars(select(Article).where(Article.version_id == version.version_id).order_by(Article.article_order)))
    if not articles or any(not article.original_text.strip() for article in articles):
        raise ValueError("法规条款原文不完整，S4 不启动")

    regulation = version.regulation
    source_document = version.source_document
    prior_s1_output = (((task.step_status or {}).get("S1") or {}).get("output") or {})
    manual_overrides = dict(prior_s1_output.get("manual_overrides") or {})
    run_id = _short_id("RUN")
    all_text = "\n".join(article.original_text for article in articles)
    config = dict(task.processing_config or {})
    config.update(
        {
            "institution_type": institution_type,
            "business_scope": business_scope or [],
            "region": region,
            "interpretation_as_of": interpretation_as_of,
            "pipeline_version": PIPELINE_VERSION,
            "pipeline_run_id": run_id,
        }
    )
    task.processing_config = config
    task.current_step = "S1"
    task.task_status = "processing"
    task.step_status = {"S1": _stage("running"), "S2": _stage("pending"), "S3": _stage("pending"), "S4": _stage("pending")}
    db.flush()
    if progress_callback:
        progress_callback("S1", "running", {})

    metadata_values = {
        "title": regulation.title,
        "document_no": regulation.document_no,
        "issuer": regulation.issuer,
        "publish_date": version.publish_date.isoformat() if version.publish_date else None,
        "effective_date": version.effective_date.isoformat() if version.effective_date else None,
    }
    metadata_fields = {
        name: _metadata_field(
            name=name,
            value=value,
            source_document=source_document,
            manual_override=manual_overrides.get(name),
        )
        for name, value in metadata_values.items()
    }
    unresolved_fields = _metadata_unresolved(metadata_fields)
    s1 = _stage(
        "completed",
        completed_at=_now(),
        output={
            **metadata_values,
            "metadata_fields": metadata_fields,
            "manual_overrides": manual_overrides,
            "article_count": len(articles),
            "page_count": source_document.page_count,
            "unresolved_fields": unresolved_fields,
            "source_document_id": source_document.document_id,
        },
    )
    task.step_status = {"S1": s1, "S2": _stage("running"), "S3": _stage("pending"), "S4": _stage("pending")}
    if progress_callback:
        progress_callback("S1", "completed", s1["output"])
        progress_callback("S2", "running", {})

    applicability = evaluate_applicability(
        regulation.title,
        all_text,
        institution_type,
        region,
        business_scope=business_scope,
        effective_date=version.effective_date,
        abolish_date=version.abolish_date,
        interpretation_as_of=interpretation_as_of,
    )
    evidence_keywords = list(dict.fromkeys([institution_type, *(business_scope or []), *("金融企业", "金融机构", "适用于", "境内", "全国", "中华人民共和国")]))
    applicability["applicability_evidence"] = _scope_evidence(
        articles,
        source_document_id=source_document.document_id,
        keywords=evidence_keywords,
    ) or [
        {
            "source_document_id": source_document.document_id,
            "page": None,
            "status": "not_found",
            "reason": "条款正文未找到可直接支持当前适用性判断的关键词定位，需人工复核。",
        }
    ]
    s2_output = {
        **applicability,
        "regulation_locator": _regulation_locator(version, s1_output=s1["output"]),
        "version_relation": _version_relation(version, all_text, source_document_id=source_document.document_id),
    }
    s2 = _stage("completed", completed_at=_now(), output=s2_output)
    task.step_status = {"S1": s1, "S2": s2, "S3": _stage("running"), "S4": _stage("pending")}
    if progress_callback:
        progress_callback("S2", "completed", s2["output"])
        progress_callback("S3", "running", {})

    requirement_objects: list[Requirement] = []
    evidence_by_article: dict[str, Evidence] = {}
    requirement_counts: dict[str, int] = {}
    for article in articles:
        evidence = Evidence(
            evidence_id=_short_id("EVID"),
            task_id=task.task_id,
            regulation_id=regulation.regulation_id,
            article_id=article.article_id,
            source_document_id=source_document.document_id,
            source_type="REGULATION_ORIGINAL",
            locator={
                "article_no": article.article_no,
                "page": article.source_page,
                **(article.source_offset or {}),
                "sha256": source_document.sha256,
            },
            source_text=article.original_text,
            description=f"{article.article_no} 原文证据；来源文件尚需人工核验后进入正式发布。",
            verification_status="needs_review",
        )
        db.add(evidence)
        evidence_by_article[article.article_id] = evidence
        parsed = extract_requirements(article)
        requirement_counts[article.article_id] = len(parsed)
        for item in parsed:
            item["requirement_id"] = f"{item['requirement_id']}_{run_id}"
            item["structured_data"] = {
                **item["structured_data"],
                "article_no": article.article_no,
                "source_locator": {
                    "source_document_id": source_document.document_id,
                    "page": article.source_page,
                    **(article.source_offset or {}),
                    "sha256": source_document.sha256,
                },
            }
            requirement = Requirement(
                **{key: value for key, value in item.items() if key not in {"structured_data"}},
                structured_data=item["structured_data"],
                pipeline_run_id=run_id,
            )
            requirement.evidence.append(evidence)
            db.add(requirement)
            requirement_objects.append(requirement)
    db.flush()
    numeric_types: dict[str, int] = {}
    numeric_expression_count = 0
    normative_term_count = 0
    for item in requirement_objects:
        numbers = item.structured_data.get("numbers") or []
        numeric_expression_count += len(numbers)
        normative_term_count += len(item.structured_data.get("normative_terms") or [])
        for number in numbers:
            numeric_type = number.get("numeric_type", "other")
            numeric_types[numeric_type] = numeric_types.get(numeric_type, 0) + 1
    s3_review_flags: list[str] = []
    if any((article.source_offset or {}).get("extraction_method") == "ocr" for article in articles):
        s3_review_flags.append("OCR_SOURCE_REQUIRES_MANUAL_TEXT_VERIFICATION")
    if any(count == 0 for count in requirement_counts.values()):
        s3_review_flags.append("DECLARATIVE_OR_NON_NORMATIVE_ARTICLE_WITHOUT_REQUIREMENT")
    s3 = _stage(
        "completed",
        completed_at=_now(),
        output={
            "requirement_count": len(requirement_objects),
            "article_count": len(articles),
            "articles_with_requirements": sum(1 for count in requirement_counts.values() if count > 0),
            "articles_without_requirements": sum(1 for count in requirement_counts.values() if count == 0),
            "numeric_requirement_count": sum(1 for item in requirement_objects if item.structured_data.get("numbers")),
            "numeric_expression_count": numeric_expression_count,
            "numeric_types": numeric_types,
            "normative_term_count": normative_term_count,
            "review_flags": s3_review_flags,
            "review_status": "needs_review",
        },
    )
    task.step_status = {"S1": s1, "S2": s2, "S3": s3, "S4": _stage("running")}
    if progress_callback:
        progress_callback("S3", "completed", s3["output"])
        progress_callback("S4", "running", {})

    from backend.app.services.version_compare import compare_regulation_versions

    relation_config = config.get("s5_relation_confirmed")
    relation_confirmed = relation_config.get("status") == "verified" if isinstance(relation_config, dict) else bool(relation_config)
    s5_result = compare_regulation_versions(version, version.previous_version, relation_confirmed=relation_confirmed)
    s5_output = s5_result["output"]

    by_article: dict[str, list[Requirement]] = {}
    for requirement in requirement_objects:
        by_article.setdefault(requirement.article_id, []).append(requirement)
    overall_evidence = list(evidence_by_article.values())[:3]
    overall_fields = build_overall_fields(
        regulation=regulation,
        version=version,
        source_document=source_document,
        articles=articles,
        requirements=requirement_objects,
        applicability=applicability,
        s5_output=s5_output,
        evidence_ids=[item.evidence_id for item in overall_evidence],
    )
    overall = Interpretation(
        interpretation_id=_short_id("INT"),
        regulation_id=regulation.regulation_id,
        article_id=None,
        summary=overall_fields["summary"],
        interpretation=overall_fields["interpretation"],
        regulatory_meaning=overall_fields["regulatory_meaning"],
        key_points=overall_fields["key_points"],
        conditions=overall_fields["conditions"],
        exceptions=overall_fields["exceptions"],
        linked_requirements=[item.requirement_id for item in requirement_objects],
        content_type="EXECUTIVE_SUMMARY",
        confidence=0.72,
        review_status="needs_review",
        fact_class="INTERPRETATION",
        content_blocks=overall_fields["content_blocks"],
        generated_by="rule_based",
        prompt_version="s4-rule-v1",
        human_lock=False,
        content_version=1,
        pipeline_run_id=run_id,
    )
    for evidence in overall_evidence:
        overall.evidence.append(evidence)
    db.add(overall)

    article_interpretations: list[Interpretation] = []
    for article in articles:
        requirements = by_article.get(article.article_id, [])
        evidence = evidence_by_article[article.article_id]
        article_fields = build_article_fields(
            article=article,
            requirements=requirements,
            evidence_id=evidence.evidence_id,
            s5_output=s5_output,
        )
        interpretation = Interpretation(
            interpretation_id=_short_id("INT"),
            regulation_id=regulation.regulation_id,
            article_id=article.article_id,
            summary=article_fields["summary"],
            interpretation=article_fields["interpretation"],
            regulatory_meaning=article_fields["regulatory_meaning"],
            key_points=article_fields["key_points"],
            conditions=article_fields["conditions"],
            exceptions=article_fields["exceptions"],
            linked_requirements=[item.requirement_id for item in requirements],
            content_type="ARTICLE",
            confidence=0.72 if requirements else 0.55,
            review_status="needs_review",
            fact_class="INTERPRETATION",
            content_blocks=article_fields["content_blocks"],
            generated_by="rule_based",
            prompt_version="s4-rule-v1",
            human_lock=False,
            content_version=1,
            pipeline_run_id=run_id,
        )
        interpretation.evidence.append(evidence)
        db.add(interpretation)
        article_interpretations.append(interpretation)

    s4 = _stage(
        "completed",
        completed_at=_now(),
        output={
            "overall_interpretation_id": overall.interpretation_id,
            "article_interpretation_count": len(article_interpretations),
            "evidence_bound_count": len(evidence_by_article),
            "change_interpretation_count": overall_fields["change_count"],
            "change_interpretation_status": overall_fields["change_interpretation_status"],
            "s5_comparison_status": s5_output.get("comparison_status"),
            "review_status": "needs_review",
            "generated_by": "rule_based",
        },
    )
    s5 = _stage(
        s5_result["stage_status"],
        completed_at=_now() if s5_result["stage_status"] == "completed" else None,
        output=s5_output,
    )
    overall.exceptions = [s5_output["reason"]]
    task.step_status = {"S1": s1, "S2": s2, "S3": s3, "S4": s4, "pipeline_run_id": run_id, "S5": s5}
    if progress_callback:
        progress_callback("S4", "completed", s4["output"])
        progress_callback("S5", "completed" if s5["status"] == "completed" else "skipped", s5["output"])
    task.current_step = "S4"
    task.task_status = "waiting_review"
    task.last_checkpoint = {"pipeline_run_id": run_id, "completed_at": _now(), "next_action": "人工复核"}
    db.commit()
    return {
        "pipeline_run_id": run_id,
        "pipeline_version": PIPELINE_VERSION,
        "task": task,
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "s4": s4,
        "overall": overall,
        "article_interpretations": article_interpretations,
        "requirements": requirement_objects,
        "evidence": list(evidence_by_article.values()),
    }
