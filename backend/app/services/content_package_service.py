"""Build immutable, shared content packages for HTML and Word consumers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import ContentPackage, ContentVersion, Interpretation, Task
from backend.app.services.evidence_service import evidence_link_payload, validate_evidence_chain


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _date(value: Any) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def _interpretation_payload(item: Interpretation) -> dict[str, Any]:
    return {
        "interpretation_id": item.interpretation_id,
        "article_id": item.article_id,
        "summary": item.summary,
        "interpretation": item.interpretation,
        "regulatory_meaning": item.regulatory_meaning,
        "key_points": item.key_points,
        "conditions": item.conditions,
        "exceptions": item.exceptions,
        "linked_requirements": item.linked_requirements,
        "content_type": item.content_type,
        "content_blocks": item.content_blocks,
        "fact_class": item.fact_class,
        "review_status": item.review_status,
        "human_lock": item.human_lock,
        "content_version": item.content_version,
        "generated_by": item.generated_by,
        "prompt_version": item.prompt_version,
    }


def build_content_package_payload(objects: dict[str, Any], task: Task, package_id: str, package_version: int) -> dict[str, Any]:
    regulation = task.regulation
    version = next((item for item in regulation.versions if item.is_current), None) if regulation else None
    overall = objects["overall"]
    article_interpretations = objects["article_interpretations"]
    requirements_by_article: dict[str, list[dict[str, Any]]] = {}
    for requirement in objects["requirements"]:
        requirements_by_article.setdefault(requirement.article_id, []).append(
            {
                "requirement_id": requirement.requirement_id,
                "article_id": requirement.article_id,
                "subject": requirement.subject,
                "rule_type": requirement.rule_type,
                "action": requirement.action,
                "object": requirement.object,
                "condition": requirement.condition,
                "deadline": requirement.deadline,
                "frequency": requirement.frequency,
                "threshold": requirement.threshold,
                "exception": requirement.exception,
                "source_text": requirement.source_text,
                "structured_data": requirement.structured_data,
                "review_status": requirement.review_status,
                "evidence_ids": [item.evidence_id for item in requirement.evidence],
            }
        )

    chapters = []
    article_navigation = []
    for item in article_interpretations:
        article = item.article
        article_no = article.article_no if article else item.article_id
        entry = {
            "article_id": item.article_id,
            "article_no": article_no,
            "article_order": article.article_order if article else None,
            "original_text": article.original_text if article else None,
            "source_page": article.source_page if article else None,
            "interpretation": _interpretation_payload(item),
            "requirements": requirements_by_article.get(item.article_id, []),
        }
        chapters.append(entry)
        article_navigation.append({"article_id": item.article_id, "article_no": article_no, "label": article_no})

    evidence_links = [evidence_link_payload(item) for item in objects["evidence"]]
    content = {
        "schema_version": "content-package-v1",
        "package_id": package_id,
        "task_id": task.task_id,
        "regulation": {
            "regulation_id": regulation.regulation_id if regulation else None,
            "title": regulation.title if regulation else None,
            "document_no": regulation.document_no if regulation else None,
            "issuer": regulation.issuer if regulation else [],
            "version_id": version.version_id if version else None,
            "version_label": version.version_label if version else None,
            "publish_date": _date(version.publish_date) if version else None,
            "effective_date": _date(version.effective_date) if version else None,
            "source_document_id": version.source_document_id if version else None,
            "source_sha256": version.source_sha256 if version else None,
        },
        "overview": _interpretation_payload(overall),
        "chapters": chapters,
        "article_navigation": article_navigation,
        "requirement_navigation": [
            {"requirement_id": item.requirement_id, "article_id": item.article_id, "label": item.requirement_id}
            for item in objects["requirements"]
        ],
        "evidence_links": evidence_links,
        "s5": (task.step_status or {}).get("S5") or {},
        "word_report_data": {"title": regulation.title if regulation else task.task_name, "sections": ["法规概览", "适用性与监管要求", "逐条解读", "版本比较", "证据链"]},
        "html_page_data": {"layout": "three_column_workbench", "left": "article_navigation", "center": "chapters", "right": "evidence_links"},
        "provenance": {"pipeline_run_id": objects["run_id"], "generated_at": _now(), "content_version": package_version},
    }
    return content


class ContentPackageNotReady(ValueError):
    def __init__(self, missing: dict[str, Any]):
        super().__init__("Content Package 尚未满足人工锁定和证据核验条件")
        self.missing = missing


def create_locked_content_package(db: Session, task: Task, *, actor_id: str) -> ContentPackage:
    from backend.app.services.review import get_latest_review_objects

    objects = get_latest_review_objects(db, task)
    missing: dict[str, Any] = {}
    interpretations_not_locked = [item.interpretation_id for item in [objects["overall"], *objects["article_interpretations"]] if item.review_status != "reviewed" or not item.human_lock]
    requirements_not_reviewed = [item.requirement_id for item in objects["requirements"] if item.review_status != "reviewed"]
    evidence_not_verified = [item.evidence_id for item in objects["evidence"] if item.verification_status != "verified"]
    chain_findings = validate_evidence_chain(objects)
    if interpretations_not_locked:
        missing["interpretations_not_locked"] = interpretations_not_locked
    if requirements_not_reviewed:
        missing["requirements_not_reviewed"] = requirements_not_reviewed
    if evidence_not_verified:
        missing["evidence_not_verified"] = evidence_not_verified
    if chain_findings:
        missing["evidence_chain_findings"] = chain_findings
    if missing:
        raise ContentPackageNotReady(missing)

    next_version = (db.scalar(select(func.max(ContentPackage.package_version)).where(ContentPackage.task_id == task.task_id)) or 0) + 1
    package_id = _id("PKG")
    content = build_content_package_payload(objects, task, package_id, next_version)
    digest = content_hash(content)
    for previous in db.scalars(select(ContentPackage).where(ContentPackage.task_id == task.task_id, ContentPackage.status == "HUMAN_LOCKED")):
        previous.status = "SUPERSEDED"
    package = ContentPackage(
        package_id=package_id,
        task_id=task.task_id,
        regulation_id=task.regulation_id,
        pipeline_run_id=objects["run_id"],
        package_version=next_version,
        status="HUMAN_LOCKED",
        content_hash=digest,
        content_json=content,
        created_by=actor_id,
        locked_by=actor_id,
    )
    db.add(package)
    return package


def record_content_version(
    db: Session,
    *,
    task: Task,
    interpretation: Interpretation,
    actor_id: str,
    before_state: dict[str, Any],
    after_state: dict[str, Any],
    change_reason: str = "人工复核保存",
) -> ContentVersion:
    snapshot = {"before": before_state, "after": after_state, "interpretation_id": interpretation.interpretation_id, "content_version": interpretation.content_version}
    version = ContentVersion(
        content_version_id=_id("CV"),
        task_id=task.task_id,
        interpretation_id=interpretation.interpretation_id,
        version_number=interpretation.content_version,
        status="HUMAN_LOCKED" if interpretation.human_lock and interpretation.review_status == "reviewed" else "DRAFT",
        content_hash=content_hash(snapshot),
        snapshot=snapshot,
        created_by=actor_id,
        change_reason=change_reason,
    )
    db.add(version)
    return version


def mark_packages_stale(db: Session, task_id: str) -> None:
    for package in db.scalars(select(ContentPackage).where(ContentPackage.task_id == task_id, ContentPackage.status == "HUMAN_LOCKED")):
        package.status = "STALE"
