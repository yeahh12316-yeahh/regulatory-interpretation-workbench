from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.schemas import (
    EvidenceRead,
    EvidenceReviewUpdate,
    ExportRead,
    InterpretationRead,
    InterpretationReviewUpdate,
    LLMReviewRead,
    MetadataReviewUpdate,
    QCReportRead,
    QCResultRead,
    RequirementRead,
    RequirementReviewUpdate,
    ReviewRead,
    ReviewDecisionRequest,
    TaskRead,
)
from backend.app.core.config import get_settings
from backend.app.db.models import Article, ContentPackage, Evidence, Interpretation, RegulationVersion, Requirement, Task
from backend.app.db.session import get_db
from backend.app.security import AuthContext, CurrentContext, require_roles
from backend.app.services.review import (
    ATTACHMENT_RESOLUTIONS,
    EVIDENCE_STATUSES,
    REVIEW_STATUSES,
    bulk_review_all,
    get_latest_review_objects,
    latest_run_id,
    review_summary,
    run_quality_check,
    write_audit,
)
from backend.app.services.content_package_service import ContentPackageNotReady, create_locked_content_package, mark_packages_stale, record_content_version
from backend.app.services.report_renderer import build_content_package_docx, check_render_consistency, render_report_html
from backend.app.services.llm_reviewer import run_llm_review


router = APIRouter(prefix="/api", tags=["human-review"])
EDIT_ROLES = ("owner", "admin", "editor", "reviewer")


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _get_task(db: Session, task_id: str, context: AuthContext) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.organization_id != context.organization.organization_id:
        raise HTTPException(status_code=404, detail="task not found")
    return task


def _objects_or_404(db: Session, task: Task):
    try:
        return get_latest_review_objects(db, task)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _review_read(db: Session, task: Task) -> ReviewRead:
    objects = _objects_or_404(db, task)
    return ReviewRead(
        pipeline_run_id=objects["run_id"],
        pipeline_version=task.processing_config.get("pipeline_version", "s1-s4-rule-based-v1"),
        task=TaskRead.model_validate(task),
        stages=task.step_status,
        overall=InterpretationRead.model_validate(objects["overall"]),
        article_interpretations=[InterpretationRead.model_validate(item) for item in objects["article_interpretations"]],
        requirements=[RequirementRead.model_validate(item) for item in objects["requirements"]],
        evidence=[EvidenceRead.model_validate(item) for item in objects["evidence"]],
        qc_results=[QCResultRead.model_validate(item) for item in objects["qc_results"]],
        audit_log_count=objects["audit_log_count"],
        review_summary=review_summary(objects),
    )


@router.get("/tasks/{task_id}/review", response_model=ReviewRead)
def get_review(task_id: str, context: CurrentContext, db: Session = Depends(get_db)) -> ReviewRead:
    task = _get_task(db, task_id, context)
    return _review_read(db, task)


@router.patch("/tasks/{task_id}/review/metadata", response_model=ReviewRead)
def update_review_metadata(
    task_id: str,
    payload: MetadataReviewUpdate,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> ReviewRead:
    task = _get_task(db, task_id, context)
    objects = _objects_or_404(db, task)
    if not task.regulation_id:
        raise HTTPException(status_code=409, detail="任务尚未绑定法规")
    version = db.scalar(select(RegulationVersion).where(RegulationVersion.regulation_id == task.regulation_id, RegulationVersion.is_current.is_(True)))
    if version is None:
        raise HTTPException(status_code=404, detail="当前法规版本不存在")
    regulation = version.regulation
    before = {
        "document_no": regulation.document_no,
        "issuer": regulation.issuer,
        "publish_date": version.publish_date.isoformat() if version.publish_date else None,
        "effective_date": version.effective_date.isoformat() if version.effective_date else None,
        "attachment_resolution": ((task.processing_config or {}).get("review_overrides") or {}).get("attachment_resolution"),
        "attachment_note": ((task.processing_config or {}).get("review_overrides") or {}).get("attachment_note"),
    }
    fields = payload.model_fields_set
    if "document_no" in fields:
        regulation.document_no = payload.document_no
    if "issuer" in fields:
        regulation.issuer = payload.issuer or []
    if "publish_date" in fields:
        version.publish_date = payload.publish_date
    if "effective_date" in fields:
        version.effective_date = payload.effective_date
    if "attachment_resolution" in fields:
        if payload.attachment_resolution is not None and payload.attachment_resolution not in ATTACHMENT_RESOLUTIONS:
            raise HTTPException(status_code=422, detail=f"attachment_resolution 必须为：{', '.join(sorted(ATTACHMENT_RESOLUTIONS))}")
        config = dict(task.processing_config or {})
        overrides = dict(config.get("review_overrides") or {})
        if payload.attachment_resolution is None:
            overrides.pop("attachment_resolution", None)
        else:
            overrides["attachment_resolution"] = payload.attachment_resolution
        config["review_overrides"] = overrides
        task.processing_config = config
    if "attachment_note" in fields:
        config = dict(task.processing_config or {})
        overrides = dict(config.get("review_overrides") or {})
        if payload.attachment_note is None:
            overrides.pop("attachment_note", None)
        else:
            overrides["attachment_note"] = payload.attachment_note.strip()
        config["review_overrides"] = overrides
        task.processing_config = config
    step_status = dict(task.step_status or {})
    s1 = dict(step_status.get("S1") or {})
    s1_output = dict(s1.get("output") or {})
    metadata_fields = dict(s1_output.get("metadata_fields") or {})
    manual_overrides = dict(s1_output.get("manual_overrides") or {})
    reviewed_at = datetime.now(timezone.utc).isoformat()
    metadata_values = {
        "document_no": regulation.document_no,
        "issuer": regulation.issuer,
        "publish_date": version.publish_date.isoformat() if version.publish_date else None,
        "effective_date": version.effective_date.isoformat() if version.effective_date else None,
    }
    for field in ("document_no", "issuer", "publish_date", "effective_date"):
        if field not in fields:
            continue
        existing = dict(metadata_fields.get(field) or {})
        manual_overrides[field] = {
            "value": metadata_values[field],
            "machine_value": existing.get("machine_value", existing.get("value")),
            "reviewed_by": context.user.user_id,
            "reviewed_at": reviewed_at,
        }
        metadata_fields[field] = {
            **existing,
            "value": metadata_values[field],
            "machine_value": manual_overrides[field]["machine_value"],
            "status": "manual_verified",
            "confidence": "high",
            "extraction_method": "manual",
            "source_document_id": version.source_document_id,
            "source_locator": {**(existing.get("source_locator") or {}), "reviewed": True},
            "reviewed_by": context.user.user_id,
            "reviewed_at": reviewed_at,
        }
    unresolved_fields = [field for field in ("document_no", "issuer", "publish_date", "effective_date") if not metadata_values[field]]
    s1_output["document_no"] = regulation.document_no
    s1_output["issuer"] = regulation.issuer
    s1_output["publish_date"] = version.publish_date.isoformat() if version.publish_date else None
    s1_output["effective_date"] = version.effective_date.isoformat() if version.effective_date else None
    s1_output["metadata_fields"] = metadata_fields
    s1_output["manual_overrides"] = manual_overrides
    s1_output["unresolved_fields"] = unresolved_fields
    s1["output"] = s1_output
    step_status["S1"] = s1
    task.step_status = step_status
    task.task_status = "reviewing"
    task.current_step = "HUMAN_REVIEW"
    mark_packages_stale(db, task.task_id)
    after = {
        "document_no": regulation.document_no,
        "issuer": regulation.issuer,
        "publish_date": version.publish_date.isoformat() if version.publish_date else None,
        "effective_date": version.effective_date.isoformat() if version.effective_date else None,
        "attachment_resolution": ((task.processing_config or {}).get("review_overrides") or {}).get("attachment_resolution"),
        "attachment_note": ((task.processing_config or {}).get("review_overrides") or {}).get("attachment_note"),
    }
    write_audit(db, task=task, actor_id=context.user.user_id, action="UPDATE_METADATA_REVIEW", entity_type="regulation_version", entity_id=version.version_id, before_state=before, after_state=after)
    db.commit()
    return _review_read(db, task)


@router.patch("/tasks/{task_id}/review/requirements/{requirement_id}", response_model=RequirementRead)
def update_requirement_review(
    task_id: str,
    requirement_id: str,
    payload: RequirementReviewUpdate,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> Requirement:
    task = _get_task(db, task_id, context)
    run_id = latest_run_id(task)
    requirement = db.get(Requirement, requirement_id)
    if requirement is None or requirement.pipeline_run_id != run_id:
        raise HTTPException(status_code=404, detail="requirement not found")
    article = db.get(Article, requirement.article_id)
    if article is None or article.version.regulation_id != task.regulation_id:
        raise HTTPException(status_code=404, detail="requirement not found")
    if payload.review_status not in REVIEW_STATUSES:
        raise HTTPException(status_code=422, detail=f"review_status 必须为：{', '.join(sorted(REVIEW_STATUSES))}")
    fields = payload.model_fields_set
    editable_fields = ("subject", "action", "object", "condition", "deadline", "frequency", "threshold", "exception", "evidence_required", "review_status")
    before = {field: getattr(requirement, field) for field in editable_fields}
    for field in editable_fields:
        if field in fields:
            setattr(requirement, field, getattr(payload, field))
    task.task_status = "reviewing"
    task.current_step = "HUMAN_REVIEW"
    after = {field: getattr(requirement, field) for field in editable_fields}
    mark_packages_stale(db, task.task_id)
    write_audit(db, task=task, actor_id=context.user.user_id, action="UPDATE_REQUIREMENT_REVIEW", entity_type="requirement", entity_id=requirement.requirement_id, before_state=before, after_state=after)
    db.commit()
    db.refresh(requirement)
    return requirement


@router.patch("/tasks/{task_id}/review/interpretations/{interpretation_id}", response_model=InterpretationRead)
def update_interpretation_review(
    task_id: str,
    interpretation_id: str,
    payload: InterpretationReviewUpdate,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> Interpretation:
    task = _get_task(db, task_id, context)
    run_id = latest_run_id(task)
    interpretation = db.get(Interpretation, interpretation_id)
    if interpretation is None or interpretation.pipeline_run_id != run_id or interpretation.regulation_id != task.regulation_id:
        raise HTTPException(status_code=404, detail="interpretation not found")
    if payload.review_status not in REVIEW_STATUSES:
        raise HTTPException(status_code=422, detail=f"review_status 必须为：{', '.join(sorted(REVIEW_STATUSES))}")
    content_fields = {"summary", "interpretation", "regulatory_meaning", "key_points", "conditions", "exceptions", "content_blocks"}
    if interpretation.human_lock and any(field in payload.model_fields_set for field in content_fields) and payload.human_lock is not False:
        raise HTTPException(status_code=409, detail="解读已锁定；修改内容前请先显式解除锁定")
    if "content_blocks" in payload.model_fields_set:
        blocks = payload.content_blocks or []
        existing_evidence_ids = {evidence.evidence_id for evidence in interpretation.evidence}
        incoming_evidence_ids = {str(value) for block in blocks for value in (block.get("evidence_ids") or [])}
        if not existing_evidence_ids.issubset(incoming_evidence_ids):
            raise HTTPException(status_code=422, detail="不能删除原有证据定位；每个解读必须保留原绑定证据")
        if any(not block.get("label") or not block.get("text") or not block.get("evidence_ids") for block in blocks):
            raise HTTPException(status_code=422, detail="每个内容块必须包含 label、text 和 evidence_ids")
    fields = payload.model_fields_set
    editable_fields = ("summary", "interpretation", "regulatory_meaning", "key_points", "conditions", "exceptions", "content_blocks", "review_status", "human_lock")
    before = {field: getattr(interpretation, field) for field in editable_fields}
    for field in editable_fields:
        if field in fields:
            setattr(interpretation, field, getattr(payload, field))
    interpretation.content_version += 1
    task.task_status = "reviewing"
    task.current_step = "HUMAN_REVIEW"
    after = {field: getattr(interpretation, field) for field in editable_fields}
    record_content_version(
        db,
        task=task,
        interpretation=interpretation,
        actor_id=context.user.user_id,
        before_state=before,
        after_state=after,
    )
    mark_packages_stale(db, task.task_id)
    write_audit(db, task=task, actor_id=context.user.user_id, action="UPDATE_INTERPRETATION_REVIEW", entity_type="interpretation", entity_id=interpretation.interpretation_id, before_state=before, after_state=after)
    db.commit()
    db.refresh(interpretation)
    return interpretation


@router.patch("/tasks/{task_id}/review/evidence/{evidence_id}", response_model=EvidenceRead)
def update_evidence_review(
    task_id: str,
    evidence_id: str,
    payload: EvidenceReviewUpdate,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> Evidence:
    task = _get_task(db, task_id, context)
    evidence = db.get(Evidence, evidence_id)
    if evidence is None or evidence.task_id != task.task_id:
        raise HTTPException(status_code=404, detail="evidence not found")
    if payload.verification_status not in EVIDENCE_STATUSES:
        raise HTTPException(status_code=422, detail=f"verification_status 必须为：{', '.join(sorted(EVIDENCE_STATUSES))}")
    before = {"verification_status": evidence.verification_status, "description": evidence.description}
    evidence.verification_status = payload.verification_status
    if "description" in payload.model_fields_set:
        evidence.description = payload.description
    after = {"verification_status": evidence.verification_status, "description": evidence.description}
    task.task_status = "reviewing"
    task.current_step = "HUMAN_REVIEW"
    mark_packages_stale(db, task.task_id)
    write_audit(db, task=task, actor_id=context.user.user_id, action="VERIFY_EVIDENCE", entity_type="evidence", entity_id=evidence.evidence_id, before_state=before, after_state=after)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.post("/tasks/{task_id}/review/qc", response_model=QCReportRead)
def run_review_qc(
    task_id: str,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> QCReportRead:
    task = _get_task(db, task_id, context)
    try:
        result = run_quality_check(db, task, actor_id=context.user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return QCReportRead(
        status=result["status"],
        task_status=result["task_status"],
        blocker_count=result["blocker_count"],
        warning_count=result["warning_count"],
        blockers=result["blockers"],
        warnings=result["warnings"],
        results=[QCResultRead.model_validate(item) for item in result["results"]],
    )


@router.post("/tasks/{task_id}/review/bulk", response_model=ReviewRead)
def bulk_review(
    task_id: str,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> ReviewRead:
    task = _get_task(db, task_id, context)
    try:
        bulk_review_all(db, task, actor_id=context.user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _review_read(db, task)


@router.post("/tasks/{task_id}/review/llm", response_model=LLMReviewRead)
def run_review_llm(
    task_id: str,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> LLMReviewRead:
    task = _get_task(db, task_id, context)
    try:
        result = run_llm_review(db, task, actor_id=context.user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return LLMReviewRead(**result)


@router.post("/tasks/{task_id}/review/decision", response_model=TaskRead)
def review_decision(
    task_id: str,
    payload: ReviewDecisionRequest,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> Task:
    task = _get_task(db, task_id, context)
    decision = payload.decision.strip().lower()
    if decision not in {"return", "approve", "publish"}:
        raise HTTPException(status_code=422, detail="decision 必须为 return、approve 或 publish")

    before = {"task_status": task.task_status, "current_step": task.current_step}
    reason = payload.reason or ("人工复核退回，需修改后重新审核" if decision == "return" else "")
    if decision == "return":
        target_type = payload.target_type
        target_id = payload.target_id
        if target_type == "interpretation" and target_id:
            interpretation = db.get(Interpretation, target_id)
            if interpretation is None or interpretation.regulation_id != task.regulation_id or interpretation.pipeline_run_id != latest_run_id(task):
                raise HTTPException(status_code=404, detail="interpretation not found")
            interpretation.review_status = "needs_review"
            interpretation.human_lock = False
            affected = {"target_type": target_type, "target_id": target_id}
        elif target_type == "requirement" and target_id:
            requirement = db.get(Requirement, target_id)
            if requirement is None or requirement.pipeline_run_id != latest_run_id(task):
                raise HTTPException(status_code=404, detail="requirement not found")
            requirement.review_status = "needs_review"
            affected = {"target_type": target_type, "target_id": target_id}
        else:
            objects = _objects_or_404(db, task)
            for interpretation in [objects["overall"], *objects["article_interpretations"]]:
                interpretation.review_status = "needs_review"
                interpretation.human_lock = False
            for requirement in objects["requirements"]:
                requirement.review_status = "needs_review"
            affected = {"target_type": "task", "target_id": task.task_id}
        task.task_status = "reviewing"
        task.current_step = "HUMAN_REVIEW"
        mark_packages_stale(db, task.task_id)
        action = "RETURN_REVIEW"
    elif decision == "approve":
        checkpoint = task.last_checkpoint or {}
        if checkpoint.get("qc_status") != "passed" or task.task_status not in {"ready_for_export", "exported"}:
            raise HTTPException(status_code=409, detail="只有最新 QC 通过后才能批准交付")
        task.task_status = "ready_for_export"
        task.current_step = "QC"
        affected = {"target_type": "task", "target_id": task.task_id}
        action = "APPROVE_REVIEW"
    else:
        checkpoint = task.last_checkpoint or {}
        if checkpoint.get("qc_status") != "passed":
            raise HTTPException(status_code=409, detail="发布前必须通过最新 QC")
        package = db.scalar(
            select(ContentPackage)
            .where(ContentPackage.task_id == task.task_id, ContentPackage.status == "HUMAN_LOCKED")
            .order_by(ContentPackage.package_version.desc(), ContentPackage.created_at.desc())
        )
        if package is None or package.status != "HUMAN_LOCKED":
            raise HTTPException(status_code=409, detail="发布前必须生成并锁定 Content Package")
        task.task_status = "published"
        task.current_step = "PUBLISH"
        affected = {"target_type": "content_package", "target_id": package.package_id}
        action = "PUBLISH_REVIEW"

    write_audit(db, task=task, actor_id=context.user.user_id, action=action, entity_type=affected["target_type"], entity_id=affected["target_id"], before_state={**before, "reason": reason}, after_state={"task_status": task.task_status, "current_step": task.current_step, "reason": reason})
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/export/docx", response_model=ExportRead)
def export_review_docx(
    task_id: str,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> ExportRead:
    task = _get_task(db, task_id, context)
    if task.task_status not in {"ready_for_export", "exported", "published"}:
        raise HTTPException(status_code=409, detail="质量检查尚未通过，不能导出交付物")
    package = db.scalar(
        select(ContentPackage)
        .where(ContentPackage.task_id == task.task_id, ContentPackage.status == "HUMAN_LOCKED")
        .order_by(ContentPackage.package_version.desc(), ContentPackage.created_at.desc())
    )
    if package is None:
        try:
            package = create_locked_content_package(db, task, actor_id=context.user.user_id)
            db.flush()
        except ContentPackageNotReady as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail={"message": str(exc), "missing": exc.missing}) from exc
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    before_task_status = task.task_status
    report_id = _id("REPORT")
    root = Path(get_settings().data_dir).expanduser().resolve()
    report_dir = root / "reports" / task.task_id
    docx_path = report_dir / f"{report_id}.docx"
    html_path = report_dir / f"{report_id}.html"
    content = dict(package.content_json or {})
    content["content_hash"] = package.content_hash
    build_content_package_docx(content, docx_path)
    render_report_html(content, html_path)
    consistency = check_render_consistency(content, html_path, docx_path)
    if consistency["status"] != "passed":
        db.rollback()
        raise HTTPException(status_code=500, detail={"message": "HTML/Word 一致性检查未通过", "consistency": consistency})
    generated_at = datetime.now(timezone.utc)
    task.task_status = "exported"
    task.current_step = "EXPORT"
    checkpoint = dict(task.last_checkpoint or {})
    checkpoint["report"] = {
        "report_id": report_id,
        "package_id": package.package_id,
        "package_version": package.package_version,
        "content_hash": package.content_hash,
        "storage_key": str(docx_path.relative_to(root)),
        "docx_storage_key": str(docx_path.relative_to(root)),
        "html_storage_key": str(html_path.relative_to(root)),
        "generated_at": generated_at.isoformat(),
        "consistency": consistency,
    }
    task.last_checkpoint = checkpoint
    write_audit(db, task=task, actor_id=context.user.user_id, action="EXPORT_REPORTS", entity_type="report", entity_id=report_id, before_state={"task_status": before_task_status}, after_state={"task_status": "exported", "report_id": report_id, "package_id": package.package_id, "consistency": consistency})
    db.commit()
    return ExportRead(
        report_id=report_id,
        task_id=task.task_id,
        file_name=docx_path.name,
        download_url=f"/api/tasks/{task.task_id}/exports/{report_id}",
        html_file_name=html_path.name,
        html_download_url=f"/api/tasks/{task.task_id}/exports/{report_id}/html",
        consistency=consistency,
        generated_at=generated_at,
        review_status="exported",
    )


@router.get("/tasks/{task_id}/exports/{report_id}")
def download_review_docx(task_id: str, report_id: str, context: CurrentContext, db: Session = Depends(get_db)) -> FileResponse:
    task = _get_task(db, task_id, context)
    report = (task.last_checkpoint or {}).get("report") or {}
    if report.get("report_id") != report_id:
        raise HTTPException(status_code=404, detail="report not found")
    root = Path(get_settings().data_dir).expanduser().resolve()
    file_path = (root / str(report.get("docx_storage_key", report.get("storage_key", "")))).resolve()
    if root not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="report file not found")
    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=file_path.name)


@router.get("/tasks/{task_id}/exports/{report_id}/html")
def download_review_html(task_id: str, report_id: str, context: CurrentContext, db: Session = Depends(get_db)) -> FileResponse:
    task = _get_task(db, task_id, context)
    report = (task.last_checkpoint or {}).get("report") or {}
    if report.get("report_id") != report_id:
        raise HTTPException(status_code=404, detail="report not found")
    root = Path(get_settings().data_dir).expanduser().resolve()
    file_path = (root / str(report.get("html_storage_key", ""))).resolve()
    if root not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="report file not found")
    return FileResponse(file_path, media_type="text/html; charset=utf-8", filename=file_path.name)
