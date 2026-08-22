"""Human review, evidence-preservation and quality-gate services for step 11."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import Article, AuditLog, Evidence, Interpretation, QCResult, Requirement, RegulationVersion, Task
from backend.app.services.evidence_service import validate_evidence_chain
from backend.app.services.content_package_service import mark_packages_stale
from backend.app.services.qc_rules import run_rule_checks
from backend.app.services.result_ordering import order_article_records


REVIEW_STATUSES = {"needs_review", "reviewing", "reviewed"}
EVIDENCE_STATUSES = {"unverified", "needs_review", "verified", "rejected"}
ATTACHMENT_RESOLUTIONS = {"needs_source", "confirmed_not_required", "supplemented"}


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def latest_run_id(task: Task) -> str | None:
    value = (task.step_status or {}).get("pipeline_run_id")
    return value if isinstance(value, str) and value else None


def _snapshot(model: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: getattr(model, field) for field in fields}


def write_audit(
    db: Session,
    *,
    task: Task,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before_state: dict[str, Any],
    after_state: dict[str, Any],
) -> AuditLog:
    entry = AuditLog(
        audit_id=_id("AUDIT"),
        task_id=task.task_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
    )
    db.add(entry)
    return entry


def get_latest_review_objects(db: Session, task: Task) -> dict[str, Any]:
    run_id = latest_run_id(task)
    if not run_id or not task.regulation_id:
        raise ValueError("S1-S4 尚未运行")
    interpretations = list(
        db.scalars(
            select(Interpretation)
            .where(Interpretation.regulation_id == task.regulation_id, Interpretation.pipeline_run_id == run_id)
            .order_by(Interpretation.article_id.is_not(None), Interpretation.created_at, Interpretation.interpretation_id)
        )
    )
    overall = next((item for item in interpretations if item.article_id is None), None)
    if overall is None:
        raise ValueError("S4结果缺少整体解读")
    articles = order_article_records([item for item in interpretations if item.article_id is not None])
    requirements = order_article_records(list(
        db.scalars(select(Requirement).where(Requirement.pipeline_run_id == run_id).order_by(Requirement.article_id, Requirement.requirement_id))
    ))
    article_ids = {item.article_id for item in articles}
    evidence = list(
        db.scalars(
            select(Evidence)
            .where(Evidence.task_id == task.task_id, Evidence.article_id.in_(article_ids | {None}))
            .order_by(Evidence.created_at, Evidence.evidence_id)
        )
    ) if article_ids else []
    qc_results = list(
        db.scalars(select(QCResult).where(QCResult.task_id == task.task_id).order_by(QCResult.created_at.desc(), QCResult.qc_id))
    )
    latest_qc_run_id = (task.last_checkpoint or {}).get("qc_run_id")
    if latest_qc_run_id:
        qc_results = [item for item in qc_results if (item.findings or {}).get("qc_run_id") == latest_qc_run_id]
    audit_count = len(list(db.scalars(select(AuditLog).where(AuditLog.task_id == task.task_id))))
    return {
        "run_id": run_id,
        "overall": overall,
        "article_interpretations": articles,
        "requirements": requirements,
        "evidence": evidence,
        "qc_results": qc_results,
        "audit_log_count": audit_count,
    }


def _linked_evidence_ids(item: Interpretation) -> set[str]:
    ids = {evidence.evidence_id for evidence in item.evidence}
    for block in item.content_blocks or []:
        ids.update(str(value) for value in (block.get("evidence_ids") or []))
    return ids


def _add_finding(
    db: Session,
    task: Task,
    *,
    target_type: str,
    target_id: str,
    check_type: str,
    status: str,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> QCResult:
    finding = QCResult(
        qc_id=_id("QC"),
        task_id=task.task_id,
        target_type=target_type,
        target_id=target_id,
        check_type=check_type,
        status=status,
        findings={"code": code, "message": message, **(details or {})},
    )
    db.add(finding)
    return finding


def run_quality_check(db: Session, task: Task, *, actor_id: str) -> dict[str, Any]:
    objects = get_latest_review_objects(db, task)
    run_id = objects["run_id"]
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    created: list[QCResult] = []
    qc_run_id = _id("QCRUN")
    previous_task_status = task.task_status

    s1_output = ((task.step_status or {}).get("S1") or {}).get("output") or {}
    for field in s1_output.get("unresolved_fields") or []:
        blockers.append({"code": "UNRESOLVED_METADATA", "target_type": "task", "target_id": task.task_id, "message": f"元数据字段待确认：{field}"})
    source_warnings: list[str] = []
    version = db.scalar(select(RegulationVersion).where(RegulationVersion.regulation_id == task.regulation_id, RegulationVersion.is_current.is_(True)))
    if version is not None:
        source_warnings = list((version.source_document.document_metadata or {}).get("warnings") or [])
    attachment_resolution = ((task.processing_config or {}).get("review_overrides") or {}).get("attachment_resolution")
    for warning in source_warnings:
        if "附件" in warning and attachment_resolution not in {"confirmed_not_required", "supplemented"}:
            blockers.append({"code": "MISSING_ATTACHMENT_SOURCE", "target_type": "source_document", "target_id": version.source_document_id if version else task.task_id, "message": warning})
        elif "附件" not in warning:
            warnings.append({"code": "SOURCE_WARNING", "target_type": "source_document", "target_id": version.source_document_id if version else task.task_id, "message": warning})

    evidence_by_id = {item.evidence_id: item for item in objects["evidence"]}
    for finding in validate_evidence_chain(objects):
        if finding["code"] in {"EVIDENCE_REFERENCE_MISSING", "EVIDENCE_LOCATOR_INCOMPLETE"}:
            blockers.append({"code": finding["code"], "target_type": "evidence", "target_id": finding["target_id"], "message": finding["message"]})
    for finding in run_rule_checks(objects):
        blockers.append({key: finding[key] for key in ("code", "target_type", "target_id", "message")})
    for interpretation in [objects["overall"], *objects["article_interpretations"]]:
        linked_ids = _linked_evidence_ids(interpretation)
        if not linked_ids or any(evidence_id not in evidence_by_id for evidence_id in linked_ids):
            blockers.append({"code": "INTERPRETATION_EVIDENCE_MISSING", "target_type": "interpretation", "target_id": interpretation.interpretation_id, "message": "解读必须绑定可定位证据。"})
        if interpretation.review_status != "reviewed" or not interpretation.human_lock:
            blockers.append({"code": "INTERPRETATION_NOT_LOCKED", "target_type": "interpretation", "target_id": interpretation.interpretation_id, "message": "解读尚未完成人工复核并锁定。"})

    for requirement in objects["requirements"]:
        if not requirement.source_text.strip():
            blockers.append({"code": "REQUIREMENT_SOURCE_EMPTY", "target_type": "requirement", "target_id": requirement.requirement_id, "message": "监管要求缺少原文片段。"})
        if not requirement.evidence:
            blockers.append({"code": "REQUIREMENT_EVIDENCE_MISSING", "target_type": "requirement", "target_id": requirement.requirement_id, "message": "监管要求必须绑定原文证据。"})
        if requirement.review_status != "reviewed":
            blockers.append({"code": "REQUIREMENT_NOT_REVIEWED", "target_type": "requirement", "target_id": requirement.requirement_id, "message": "监管要求尚未完成逐项人工复核。"})

    for evidence in objects["evidence"]:
        if evidence.verification_status != "verified":
            blockers.append({"code": "EVIDENCE_NOT_VERIFIED", "target_type": "evidence", "target_id": evidence.evidence_id, "message": "证据尚未人工核验。"})

    s5 = (task.step_status or {}).get("S5") or {}
    if s5.get("status") == "skipped":
        warnings.append({"code": "S5_SKIPPED", "target_type": "task", "target_id": task.task_id, "message": (s5.get("output") or {}).get("reason") or s5.get("reason") or "未提供已核验旧版，版本比较未启用。"})
    elif s5.get("status") == "blocked":
        blockers.append({"code": "S5_NOT_READY", "target_type": "task", "target_id": task.task_id, "message": (s5.get("output") or {}).get("reason") or "S5 的版本关系或来源尚未核验。"})

    llm_results = list(
        db.scalars(
            select(QCResult)
            .where(QCResult.task_id == task.task_id, QCResult.check_type == "LLM_REVIEW")
            .order_by(QCResult.created_at.desc(), QCResult.qc_id)
        )
    )
    llm_required = bool((task.processing_config or {}).get("llm_reviewer_required", get_settings().llm_reviewer_required))
    if not llm_results:
        finding = {"code": "LLM_REVIEW_NOT_RUN", "target_type": "task", "target_id": task.task_id, "message": "LLM Reviewer 尚未运行；当前 QC 只允许以规则 QC 结果作为事实闸门。"}
        (blockers if llm_required else warnings).append(finding)
    else:
        latest_llm = llm_results[0]
        llm_status = latest_llm.status
        if llm_status == "passed":
            pass
        elif llm_status == "not_configured":
            finding = {"code": "LLM_REVIEW_NOT_CONFIGURED", "target_type": "task", "target_id": task.task_id, "message": "LLM Reviewer 未配置模型、Provider 或 API Key，不能声称已完成模型复核。"}
            (blockers if llm_required else warnings).append(finding)
        else:
            details = latest_llm.findings or {}
            finding = {"code": details.get("code", "LLM_REVIEW_NEEDS_REVISION"), "target_type": "task", "target_id": task.task_id, "message": details.get("message", "LLM Reviewer 返回了需要处理的结果。")}
            (blockers if llm_required or llm_status == "blocker" else warnings).append(finding)

    for finding in blockers:
        created.append(_add_finding(db, task, target_type=finding["target_type"], target_id=finding["target_id"], check_type="REVIEW_GATE", status="blocker", code=finding["code"], message=finding["message"], details={"qc_run_id": qc_run_id}))
    for finding in warnings:
        created.append(_add_finding(db, task, target_type=finding["target_type"], target_id=finding["target_id"], check_type="REVIEW_GATE", status="warning", code=finding["code"], message=finding["message"], details={"qc_run_id": qc_run_id}))
    if not blockers:
        created.append(_add_finding(db, task, target_type="task", target_id=task.task_id, check_type="REVIEW_GATE", status="passed", code="REVIEW_GATE_PASSED", message="人工复核、证据和交付前质量检查均已通过。", details={"qc_run_id": qc_run_id}))

    status = "blocked" if blockers else "passed"
    task.task_status = "reviewing" if blockers else "ready_for_export"
    task.current_step = "QC"
    task.last_checkpoint = {"pipeline_run_id": run_id, "qc_run_id": qc_run_id, "qc_status": status, "blocker_count": len(blockers), "warning_count": len(warnings), "completed_at": _now()}
    write_audit(
        db,
        task=task,
        actor_id=actor_id,
        action="RUN_QC",
        entity_type="task",
        entity_id=task.task_id,
        before_state={"task_status": previous_task_status},
        after_state={"task_status": task.task_status, "qc_status": status, "blocker_count": len(blockers), "warning_count": len(warnings)},
    )
    db.commit()
    return {"status": status, "task_status": task.task_status, "blocker_count": len(blockers), "warning_count": len(warnings), "blockers": blockers, "warnings": warnings, "results": created}


def review_summary(objects: dict[str, Any]) -> dict[str, Any]:
    return {
        "qc_status": None,
        "reviewed_requirements": sum(item.review_status == "reviewed" for item in objects["requirements"]),
        "total_requirements": len(objects["requirements"]),
        "locked_interpretations": sum(item.human_lock and item.review_status == "reviewed" for item in [objects["overall"], *objects["article_interpretations"]]),
        "total_interpretations": 1 + len(objects["article_interpretations"]),
        "verified_evidence": sum(item.verification_status == "verified" for item in objects["evidence"]),
        "total_evidence": len(objects["evidence"]),
    }


def bulk_review_all(db: Session, task: Task, *, actor_id: str) -> dict[str, int]:
    """Mark generated review objects in one audited transaction.

    Metadata and attachment scope remain separate human decisions and are not
    fabricated by this bulk action.
    """
    objects = get_latest_review_objects(db, task)
    before_status = task.task_status
    counts = {"requirements": 0, "interpretations": 0, "evidence": 0}

    for requirement in objects["requirements"]:
        before = _snapshot(requirement, ("review_status",))
        if requirement.review_status != "reviewed":
            requirement.review_status = "reviewed"
            counts["requirements"] += 1
            write_audit(db, task=task, actor_id=actor_id, action="BULK_REVIEW_REQUIREMENT", entity_type="requirement", entity_id=requirement.requirement_id, before_state=before, after_state={"review_status": "reviewed", "bulk": True})

    for interpretation in [objects["overall"], *objects["article_interpretations"]]:
        before = _snapshot(interpretation, ("review_status", "human_lock"))
        if interpretation.review_status != "reviewed" or not interpretation.human_lock:
            interpretation.review_status = "reviewed"
            interpretation.human_lock = True
            counts["interpretations"] += 1
            write_audit(db, task=task, actor_id=actor_id, action="BULK_REVIEW_INTERPRETATION", entity_type="interpretation", entity_id=interpretation.interpretation_id, before_state=before, after_state={"review_status": "reviewed", "human_lock": True, "bulk": True})

    for evidence in objects["evidence"]:
        before = _snapshot(evidence, ("verification_status",))
        if evidence.verification_status != "verified":
            evidence.verification_status = "verified"
            counts["evidence"] += 1
            write_audit(db, task=task, actor_id=actor_id, action="BULK_VERIFY_EVIDENCE", entity_type="evidence", entity_id=evidence.evidence_id, before_state=before, after_state={"verification_status": "verified", "bulk": True})

    task.task_status = "reviewing"
    task.current_step = "HUMAN_REVIEW"
    mark_packages_stale(db, task.task_id)
    write_audit(db, task=task, actor_id=actor_id, action="BULK_REVIEW_ALL", entity_type="task", entity_id=task.task_id, before_state={"task_status": before_status}, after_state={"task_status": task.task_status, "counts": counts, "metadata_requires_manual_confirmation": True})
    db.commit()
    return counts
