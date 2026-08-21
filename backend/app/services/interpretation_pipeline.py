"""Evidence-first S1-S4 regulatory interpretation pipeline.

The first production slice intentionally uses deterministic extraction and
templated interpretation. It is executable without a model key, preserves the
source text verbatim, and marks every generated result for human review. A
model provider can be introduced behind the same result contract later without
changing the evidence or database boundary.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Article, Evidence, Interpretation, RegulationVersion, Requirement, Task


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
)
_NUMBER_PATTERN = re.compile(
    r"(?:第[一二三四五六七八九十百千万零〇]+条|\d+(?:\.\d+)?(?:%|％|年|个月|月|日|天|小时|万元|元|次)?|[一二三四五六七八九十百千万零〇]+(?:年|个月|月|日|天|次))"
)
_TIME_PATTERN = re.compile(r"(?:\d+(?:\.\d+)?|[一二三四五六七八九十百千万零〇]+)(?:年|个月|月|日|天|小时)(?:内|以内|后|前)?")
_FREQUENCY_PATTERN = re.compile(r"(?:每(?:年|月|季度|日)|定期|不定期|及时|持续|按期|至少每[^，。；]{0,12})")


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


def _extract_conditions(text: str) -> list[str]:
    candidates = re.findall(r"(?:在|如|当|根据|按照|经|除)[^，。；]{1,48}", text)
    return list(dict.fromkeys(candidate.strip() for candidate in candidates))


def _extract_exceptions(text: str) -> list[str]:
    candidates = re.findall(r"(?:除|但)[^，。；]{1,48}(?:外|除外)", text)
    return list(dict.fromkeys(candidate.strip() for candidate in candidates))


def _extract_numbers(text: str) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for match in _NUMBER_PATTERN.finditer(text):
        expression = match.group(0)
        values.append({"original_expression": expression, "start": str(match.start()), "end": str(match.end())})
    return values


def _extract_requirement(article: Article, segment: str, index: int) -> dict[str, Any]:
    modal = _first_modal(segment)
    if modal is None:
        rule_type = "SCOPE" if any(keyword in segment for keyword in ("适用", "适用于", "范围")) else "OTHER"
        subject = "本条规定的责任主体"
        action = None
        object_text = segment
    else:
        position, keyword, rule_type = modal
        before = re.split(r"[，。；;]", segment[:position])[-1].strip()
        subject = before[-80:] if before else "本条规定的责任主体"
        action_text = segment[position + len(keyword):].strip(" ：:，,。；;")
        action = keyword
        object_text = action_text[:240] or None

    numbers = _extract_numbers(segment)
    deadline_match = _TIME_PATTERN.search(segment)
    frequency_match = _FREQUENCY_PATTERN.search(segment)
    threshold = None
    if any(token in segment for token in ("至少", "不超过", "不少于", "不低于", "超过", "%", "％")):
        threshold = segment[:300]

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
        "exception": "；".join(_extract_exceptions(segment)) or None,
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
            "exceptions": _extract_exceptions(segment),
        },
    }


def extract_requirements(article: Article) -> list[dict[str, Any]]:
    segments = _split_sentences(article.original_text)
    extracted: list[dict[str, Any]] = []
    for segment in segments:
        if _first_modal(segment) or any(keyword in segment for keyword in ("适用于", "适用范围", "定义", "不得", "应当", "必须")):
            extracted.append(_extract_requirement(article, segment, len(extracted) + 1))
    if not extracted:
        extracted.append(_extract_requirement(article, article.original_text.strip(), 1))
    return extracted


def evaluate_applicability(
    regulation_title: str,
    article_text: str,
    institution_type: str,
    region: str | None,
) -> dict[str, Any]:
    text = f"{regulation_title}\n{article_text}"
    institution_match = bool(institution_type and (institution_type in text or "金融企业" in text or "金融机构" in text))
    explicit_scope = any(keyword in text for keyword in ("适用于", "适用范围", "金融企业", "金融机构", "商业银行"))
    regional_match = True if not region else ("境内" in text or "全国" in text or "中华人民共和国" in text or region in text)
    if explicit_scope and institution_match and regional_match:
        status = "DIRECTLY_APPLICABLE"
        confidence = "medium"
        reason = f"原文出现金融机构适用范围，当前机构类型为“{institution_type}”；地域/时点未发现冲突。"
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
        "region": region,
        "matching_stage": {
            "institution_type_match": institution_match,
            "business_scope_match": None,
            "regional_temporal_match": regional_match,
        },
        "reason": reason,
        "evidence_required": True,
    }


def _stage(status: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, "version": 1, **extra}


def run_s1_s4_pipeline(
    db: Session,
    task: Task,
    *,
    institution_type: str,
    business_scope: list[str] | None = None,
    region: str | None = "中国境内",
    interpretation_as_of: str | None = None,
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

    unresolved_fields: list[str] = []
    if not regulation.document_no:
        unresolved_fields.append("document_no")
    s1 = _stage(
        "completed",
        completed_at=_now(),
        output={
            "title": regulation.title,
            "document_no": regulation.document_no,
            "issuer": regulation.issuer,
            "publish_date": version.publish_date.isoformat() if version.publish_date else None,
            "effective_date": version.effective_date.isoformat() if version.effective_date else None,
            "article_count": len(articles),
            "page_count": source_document.page_count,
            "unresolved_fields": unresolved_fields,
            "source_document_id": source_document.document_id,
        },
    )
    task.step_status = {"S1": s1, "S2": _stage("running"), "S3": _stage("pending"), "S4": _stage("pending")}

    applicability = evaluate_applicability(regulation.title, all_text, institution_type, region)
    s2 = _stage("completed", completed_at=_now(), output=applicability)
    task.step_status = {"S1": s1, "S2": s2, "S3": _stage("running"), "S4": _stage("pending")}

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
            requirement = Requirement(
                **{key: value for key, value in item.items() if key not in {"structured_data"}},
                structured_data=item["structured_data"],
                pipeline_run_id=run_id,
            )
            requirement.evidence.append(evidence)
            db.add(requirement)
            requirement_objects.append(requirement)
    db.flush()
    s3 = _stage(
        "completed",
        completed_at=_now(),
        output={
            "requirement_count": len(requirement_objects),
            "article_count": len(articles),
            "articles_with_requirements": sum(1 for count in requirement_counts.values() if count > 0),
            "numeric_requirement_count": sum(1 for item in requirement_objects if item.structured_data.get("numbers")),
            "review_status": "needs_review",
        },
    )
    task.step_status = {"S1": s1, "S2": s2, "S3": s3, "S4": _stage("running")}

    by_article: dict[str, list[Requirement]] = {}
    for requirement in requirement_objects:
        by_article.setdefault(requirement.article_id, []).append(requirement)
    key_points = [
        f"{item.subject}：{item.action or '应关注'} {item.object or item.source_text[:80]}"
        for item in requirement_objects[:6]
    ]
    overall_evidence = list(evidence_by_article.values())[:3]
    overall = Interpretation(
        interpretation_id=_short_id("INT"),
        regulation_id=regulation.regulation_id,
        article_id=None,
        summary=f"{regulation.title}已完成法规元数据、适用性和条款要求抽取；当前结果为规则生成，需人工复核。",
        interpretation=(
            f"本次解读基于已登记的《{regulation.title}》{version.version_label}原文，识别出 {len(articles)} 个条款和 "
            f"{len(requirement_objects)} 个监管要求。当前机构类型为“{institution_type}”，适用性判断为“{applicability['status']}”。"
        ),
        regulatory_meaning="系统仅根据已登记原文和结构化要求生成监管侧初步解读，不扩展至内部制度、整改或审计结论。",
        key_points=key_points,
        conditions=[applicability["reason"]],
        exceptions=["2015年旧版未提供，S5变化解读不生成。"],
        linked_requirements=[item.requirement_id for item in requirement_objects],
        content_type="EXECUTIVE_SUMMARY",
        confidence=0.72,
        review_status="needs_review",
        fact_class="INTERPRETATION",
        content_blocks=[
            {"label": "FACT", "text": f"法规原文共 {len(articles)} 条，来源文件 {source_document.file_name}，共 {source_document.page_count or '未知'} 页。", "evidence_ids": [item.evidence_id for item in overall_evidence]},
            {"label": "OFFICIAL", "text": f"法规发布机关：{'、'.join(regulation.issuer) or '待确认'}；生效日期：{version.effective_date.isoformat() if version.effective_date else '待确认'}。", "evidence_ids": [item.evidence_id for item in overall_evidence]},
            {"label": "INTERPRETATION", "text": "本结果是基于原文的可追溯初步解读，必须经人工复核后才能作为正式交付物。", "evidence_ids": [item.evidence_id for item in overall_evidence]},
        ],
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
        points = [f"{item.action or '识别到规则'}：{item.object or item.source_text[:100]}" for item in requirements]
        interpretation = Interpretation(
            interpretation_id=_short_id("INT"),
            regulation_id=regulation.regulation_id,
            article_id=article.article_id,
            summary=f"{article.article_no}：{points[0] if points else '原文已载入，暂未识别出明确行为义务。'}",
            interpretation=(
                f"{article.article_no}的原文要求主体“{requirements[0].subject}”"
                f"{requirements[0].action or '关注'}相关事项；具体条件、例外、时限和数字以原文证据为准。"
                if requirements
                else f"{article.article_no}暂未识别出明确的行为义务，不能据此扩展监管要求，需人工复核。"
            ),
            regulatory_meaning="该条解读仅对已抽取的原文结构进行说明，不替代正式法律意见。",
            key_points=points,
            conditions=list(dict.fromkeys(item.condition for item in requirements if item.condition)),
            exceptions=list(dict.fromkeys(item.exception for item in requirements if item.exception)),
            linked_requirements=[item.requirement_id for item in requirements],
            content_type="ARTICLE",
            confidence=0.72 if requirements else 0.55,
            review_status="needs_review",
            fact_class="INTERPRETATION",
            content_blocks=[
                {"label": "FACT", "text": article.original_text, "evidence_ids": [evidence.evidence_id]},
                {"label": "OFFICIAL", "text": f"证据定位：第 {article.source_page or '待确认'} 页，{article.article_no}。", "evidence_ids": [evidence.evidence_id]},
                {"label": "INTERPRETATION", "text": "以上为基于条款结构的初步解释，当前状态为待人工复核。", "evidence_ids": [evidence.evidence_id]},
            ],
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
            "review_status": "needs_review",
            "generated_by": "rule_based",
        },
    )
    task.step_status = {"S1": s1, "S2": s2, "S3": s3, "S4": s4, "pipeline_run_id": run_id, "S5": {"status": "skipped", "reason": "用户未提供已核验的2015年旧版"}}
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
