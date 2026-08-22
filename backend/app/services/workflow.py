"""Durable workflow orchestration for regulation interpretation tasks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import Task, WorkflowNode, WorkflowRun
from backend.app.db.session import SessionLocal
from backend.app.services.interpretation_pipeline import run_s1_s4_pipeline


WORKFLOW_NODES = ("S1", "S2", "S3", "S4", "S5")
NODE_WEIGHTS = {"S1": 10, "S2": 20, "S3": 30, "S4": 30, "S5": 10}
NODE_SEQUENCE = {name: index for index, name in enumerate(WORKFLOW_NODES, start=1)}
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _progress(nodes: list[WorkflowNode]) -> int:
    completed = 0.0
    for node in nodes:
        completed += NODE_WEIGHTS[node.node_name] * max(0, min(node.progress, 100)) / 100
    return int(round(completed))


def _checkpoint(task: Task, workflow: WorkflowRun) -> None:
    checkpoint = dict(task.last_checkpoint or {})
    checkpoint["workflow_id"] = workflow.workflow_id
    checkpoint["workflow_status"] = workflow.status
    checkpoint["workflow_progress"] = workflow.progress
    checkpoint["workflow_current_node"] = workflow.current_node
    checkpoint["workflow_updated_at"] = _now_iso()
    task.last_checkpoint = checkpoint


def _write_audit(db: Session, task: Task, *, actor_id: str, action: str, workflow: WorkflowRun, detail: dict[str, Any]) -> None:
    from backend.app.services.review import write_audit

    write_audit(
        db,
        task=task,
        actor_id=actor_id,
        action=action,
        entity_type="workflow",
        entity_id=workflow.workflow_id,
        before_state={},
        after_state={"workflow_id": workflow.workflow_id, **detail},
    )


def create_workflow(
    db: Session,
    task: Task,
    *,
    actor_id: str,
    params: dict[str, Any],
    requested_from: str = "S1",
    parent_workflow_id: str | None = None,
) -> WorkflowRun:
    requested_from = requested_from.upper()
    if requested_from not in WORKFLOW_NODES:
        raise ValueError(f"requested_from 必须为：{', '.join(WORKFLOW_NODES)}")
    workflow = WorkflowRun(
        workflow_id=_id("WF"),
        task_id=task.task_id,
        workflow_type="REGULATION_INTERPRETATION",
        status="queued",
        current_node=requested_from,
        progress=0,
        requested_from=requested_from,
        params=params,
        error_state={},
        retry_count=0,
        max_retries=2,
        parent_workflow_id=parent_workflow_id,
        requested_by=actor_id,
    )
    workflow.nodes = [
        WorkflowNode(
            node_id=_id("WFNODE"),
            node_name=node_name,
            sequence=NODE_SEQUENCE[node_name],
            status="pending",
            attempt=0,
            progress=0,
            output={},
            error_state={},
        )
        for node_name in WORKFLOW_NODES
    ]
    db.add(workflow)
    task.task_status = "queued"
    task.current_step = "WORKFLOW"
    task.error_state = {}
    _checkpoint(task, workflow)
    _write_audit(db, task, actor_id=actor_id, action="CREATE_WORKFLOW", workflow=workflow, detail={"status": "queued", "requested_from": requested_from})
    db.commit()
    db.refresh(workflow)
    return workflow


def _find_node(workflow: WorkflowRun, node_name: str) -> WorkflowNode:
    node = next((item for item in workflow.nodes if item.node_name == node_name), None)
    if node is None:
        raise ValueError(f"workflow 缺少节点：{node_name}")
    return node


def _update_node(
    db: Session,
    workflow: WorkflowRun,
    task: Task,
    node_name: str,
    status: str,
    *,
    output: dict[str, Any] | None = None,
    error_state: dict[str, Any] | None = None,
) -> None:
    node = _find_node(workflow, node_name)
    if status == "running":
        node.attempt += 1
        node.started_at = _now()
        node.completed_at = None
        node.progress = 5
        node.error_state = {}
        workflow.current_node = node_name
    elif status == "completed":
        node.status = "completed"
        node.progress = 100
        node.completed_at = _now()
        node.output = output or {}
    elif status == "skipped":
        node.status = "skipped"
        node.progress = 100
        node.completed_at = _now()
        node.output = output or {}
    elif status == "failed":
        node.status = "failed"
        node.progress = 0
        node.completed_at = _now()
        node.error_state = error_state or {}
    else:
        node.status = status
    if status == "running":
        node.status = "running"
    workflow.progress = _progress(workflow.nodes)
    _checkpoint(task, workflow)
    db.commit()


class WorkflowNodeError(RuntimeError):
    def __init__(self, node_name: str, message: str):
        super().__init__(message)
        self.node_name = node_name


def execute_workflow(db: Session, workflow_id: str) -> WorkflowRun:
    workflow = db.get(WorkflowRun, workflow_id)
    if workflow is None:
        raise ValueError("workflow not found")
    task = db.get(Task, workflow.task_id)
    if task is None:
        raise ValueError("workflow task not found")
    if workflow.status == "completed":
        return workflow

    workflow.status = "running"
    workflow.started_at = workflow.started_at or _now()
    workflow.current_node = workflow.requested_from
    task.task_status = "processing"
    task.current_step = workflow.requested_from
    _checkpoint(task, workflow)
    db.commit()

    failure_node = str((workflow.params or {}).get("workflow_fail_at") or "").upper()

    def progress_callback(node_name: str, status: str, output: dict[str, Any] | None = None) -> None:
        if status == "running" and failure_node == node_name:
            _update_node(db, workflow, task, node_name, "running", output={})
            raise WorkflowNodeError(node_name, f"按测试配置在 {node_name} 节点注入失败")
        _update_node(db, workflow, task, node_name, status, output=output)

    try:
        run_s1_s4_pipeline(
            db,
            task,
            institution_type=str((workflow.params or {}).get("institution_type") or "商业银行"),
            business_scope=list((workflow.params or {}).get("business_scope") or []),
            region=(workflow.params or {}).get("region") or "中国境内",
            interpretation_as_of=(workflow.params or {}).get("interpretation_as_of"),
            progress_callback=progress_callback,
        )
        for node_name in WORKFLOW_NODES:
            node = _find_node(workflow, node_name)
            if node.status not in {"completed", "skipped"}:
                stage = (task.step_status or {}).get(node_name) or {}
                output = stage.get("output") or {}
                stage_status = stage.get("status")
                status = "skipped" if stage_status == "skipped" else ("blocked" if stage_status in {"blocked", "waiting"} else "completed")
                _update_node(db, workflow, task, node_name, status, output=output)
        workflow.status = "completed"
        workflow.current_node = None
        workflow.progress = 100
        workflow.completed_at = _now()
        task.task_status = "waiting_review"
        task.current_step = "HUMAN_REVIEW"
        _checkpoint(task, workflow)
        db.commit()
        return workflow
    except Exception as exc:
        db.rollback()
        workflow = db.get(WorkflowRun, workflow_id)
        task = db.get(Task, workflow.task_id) if workflow else None
        if workflow is None or task is None:
            raise
        node_name = workflow.current_node or workflow.requested_from
        workflow.status = "failed"
        workflow.error_state = {"code": "WORKFLOW_NODE_FAILED", "node": node_name, "message": str(exc), "retryable": workflow.retry_count < workflow.max_retries}
        workflow.completed_at = _now()
        node = _find_node(workflow, node_name)
        node.status = "failed"
        node.completed_at = _now()
        node.error_state = workflow.error_state
        task.task_status = "failed"
        task.current_step = node_name
        task.error_state = workflow.error_state
        _checkpoint(task, workflow)
        db.commit()
        return workflow


def retry_workflow(db: Session, workflow: WorkflowRun, *, actor_id: str) -> WorkflowRun:
    if workflow.status != "failed":
        raise ValueError("只有失败的 workflow 才能重试")
    if workflow.retry_count >= workflow.max_retries:
        raise ValueError("已达到 workflow 最大重试次数")
    workflow.retry_count += 1
    workflow.status = "queued"
    workflow.error_state = {}
    workflow.completed_at = None
    workflow.current_node = workflow.requested_from
    for node in workflow.nodes:
        node.status = "pending"
        node.progress = 0
        node.error_state = {}
        node.completed_at = None
    task = workflow.task
    task.task_status = "queued"
    task.current_step = "WORKFLOW"
    task.error_state = {}
    _checkpoint(task, workflow)
    _write_audit(db, task, actor_id=actor_id, action="RETRY_WORKFLOW", workflow=workflow, detail={"retry_count": workflow.retry_count, "status": "queued"})
    db.commit()
    return workflow


def rerun_workflow_node(db: Session, workflow: WorkflowRun, *, actor_id: str, node_name: str) -> WorkflowRun:
    node_name = node_name.upper()
    if node_name not in WORKFLOW_NODES:
        raise ValueError(f"node_name 必须为：{', '.join(WORKFLOW_NODES)}")
    if workflow.status not in TERMINAL_STATUSES:
        raise ValueError("workflow 仍在运行，不能创建节点重跑")
    task = workflow.task
    new_workflow = create_workflow(
        db,
        task,
        actor_id=actor_id,
        params={**(workflow.params or {}), "rerun_node": node_name, "rerun_note": "为保证 S1-S5 数据一致性，从请求节点重新计算完整解释流水线"},
        requested_from=node_name,
        parent_workflow_id=workflow.workflow_id,
    )
    return new_workflow


def dispatch_workflow(db: Session, workflow: WorkflowRun) -> str | None:
    settings = get_settings()
    if settings.workflow_execution_mode.lower() == "inline":
        execute_workflow(db, workflow.workflow_id)
        return None
    try:
        from worker.app.celery_app import celery_app

        async_result = celery_app.send_task("workflow.execute", args=[workflow.workflow_id])
        workflow.celery_task_id = async_result.id
        db.commit()
        return async_result.id
    except Exception:
        if not settings.workflow_allow_inline_fallback:
            raise
        execute_workflow(db, workflow.workflow_id)
        return None


def execute_workflow_from_worker(workflow_id: str) -> None:
    with SessionLocal() as db:
        execute_workflow(db, workflow_id)
