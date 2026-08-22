from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.db.models import RegulationVersion, Task, VersionRelation, WorkflowRun
from backend.app.db.session import get_db
from backend.app.services.comparison_sync import sync_workflow_s5_node
from backend.app.security import AuthContext, require_roles
from backend.app.services.review import write_audit
from backend.app.services.version_compare import compare_regulation_versions


router = APIRouter(prefix="/api", tags=["s5-comparison"])
EDIT_ROLES = ("owner", "admin", "editor", "reviewer")


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_task(db: Session, task_id: str, context: AuthContext) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.organization_id != context.organization.organization_id:
        raise HTTPException(status_code=404, detail="task not found")
    return task


def _current_version(db: Session, task: Task) -> RegulationVersion:
    if not task.regulation_id:
        raise HTTPException(status_code=409, detail="任务尚未绑定法规")
    version = db.scalar(
        select(RegulationVersion)
        .where(RegulationVersion.regulation_id == task.regulation_id, RegulationVersion.is_current.is_(True))
        .order_by(RegulationVersion.created_at.desc())
    )
    if version is None:
        raise HTTPException(status_code=404, detail="当前法规版本不存在")
    return version


def _relation_confirmed(db: Session, task: Task, current: RegulationVersion) -> bool:
    previous = current.previous_version
    if previous is None:
        return False
    relation = db.scalar(
        select(VersionRelation).where(
            VersionRelation.regulation_id == task.regulation_id,
            VersionRelation.from_version_id == previous.version_id,
            VersionRelation.to_version_id == current.version_id,
            VersionRelation.status == "verified",
        )
    )
    return relation is not None


def _write_s5_stage(task: Task, comparison: dict[str, Any]) -> dict[str, Any]:
    stage_status = comparison["stage_status"]
    stage = {"status": stage_status, "version": 1, "output": comparison["output"]}
    if stage_status == "completed":
        stage["completed_at"] = _now()
    task.step_status = {**(task.step_status or {}), "S5": stage}
    task.current_step = "S5"
    task.task_status = "waiting_review" if stage_status in {"completed", "skipped"} else "reviewing"
    task.last_checkpoint = {"completed_at": _now(), "next_action": "人工复核 S5" if stage_status == "completed" else comparison["output"].get("reason")}
    return stage


@router.post("/tasks/{task_id}/s5/confirm-relation", status_code=status.HTTP_200_OK)
def confirm_s5_relation(
    task_id: str,
    payload: dict[str, Any] | None = Body(default=None),
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    task = _get_task(db, task_id, context)
    current = _current_version(db, task)
    previous = current.previous_version
    if previous is None:
        raise HTTPException(status_code=409, detail="当前法规没有已登记的前一版本；请先补充旧规原文并完成版本登记")
    if not previous.source_document_id or not previous.source_sha256:
        raise HTTPException(status_code=409, detail="旧规来源文件或文件哈希缺失，不能确认版本关系")

    relation = db.scalar(
        select(VersionRelation).where(
            VersionRelation.regulation_id == task.regulation_id,
            VersionRelation.from_version_id == previous.version_id,
            VersionRelation.to_version_id == current.version_id,
        )
    )
    before = {
        "status": relation.status if relation else None,
        "from_version_id": previous.version_id,
        "to_version_id": current.version_id,
    }
    if relation is None:
        relation = VersionRelation(
            relation_id=_id("REL"),
            regulation_id=task.regulation_id,
            from_version_id=previous.version_id,
            to_version_id=current.version_id,
            relation_type="SUPERSEDES",
        )
        db.add(relation)
    relation.status = "verified"
    relation.relation_metadata = {
        "confirmed_by": context.user.user_id,
        "confirmed_at": _now(),
        "note": (payload or {}).get("note"),
        "old_source_sha256": previous.source_sha256,
        "new_source_sha256": current.source_sha256,
    }
    config = dict(task.processing_config or {})
    config["s5_relation_confirmed"] = {"status": "verified", "relation_id": relation.relation_id, "confirmed_by": context.user.user_id, "confirmed_at": _now()}
    task.processing_config = config
    task.current_step = "S5"
    task.task_status = "reviewing"
    write_audit(
        db,
        task=task,
        actor_id=context.user.user_id,
        action="CONFIRM_S5_VERSION_RELATION",
        entity_type="version_relation",
        entity_id=relation.relation_id,
        before_state=before,
        after_state={"status": relation.status, "from_version_id": previous.version_id, "to_version_id": current.version_id},
    )
    db.commit()
    db.refresh(relation)
    return {
        "task_id": task.task_id,
        "relation_id": relation.relation_id,
        "status": relation.status,
        "from_version_id": relation.from_version_id,
        "to_version_id": relation.to_version_id,
        "message": "版本关系已确认；下一步可运行 S5 条款比较。",
    }


@router.post("/tasks/{task_id}/s5/compare", status_code=status.HTTP_200_OK)
def run_s5_comparison(
    task_id: str,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    task = _get_task(db, task_id, context)
    current = _current_version(db, task)
    before_stage = (task.step_status or {}).get("S5")
    comparison = compare_regulation_versions(current, current.previous_version, relation_confirmed=_relation_confirmed(db, task, current))
    stage = _write_s5_stage(task, comparison)
    workflow = db.scalar(select(WorkflowRun).where(WorkflowRun.task_id == task.task_id).order_by(desc(WorkflowRun.created_at)))
    if workflow is not None:
        sync_workflow_s5_node(workflow, stage)
    write_audit(
        db,
        task=task,
        actor_id=context.user.user_id,
        action="RUN_S5_COMPARISON",
        entity_type="task",
        entity_id=task.task_id,
        before_state={"S5": before_stage},
        after_state={"S5": stage},
    )
    db.commit()
    return {"task_id": task.task_id, "stage": stage, "comparison": comparison["output"]}
