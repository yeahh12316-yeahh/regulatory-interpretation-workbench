from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.schemas import TaskRead, WorkflowRead, WorkflowRerunRequest, WorkflowStartRequest
from backend.app.db.models import Task, WorkflowRun
from backend.app.db.session import get_db
from backend.app.security import AuthContext, CurrentContext, require_roles
from backend.app.services.workflow import create_workflow, dispatch_workflow, rerun_workflow_node as create_node_rerun, retry_workflow


router = APIRouter(prefix="/api", tags=["workflow"])
EDIT_ROLES = ("owner", "admin", "editor")


def _get_task(db: Session, task_id: str, context: AuthContext | CurrentContext) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.organization_id != context.organization.organization_id:
        raise HTTPException(status_code=404, detail="task not found")
    return task


def _get_workflow(db: Session, workflow_id: str, context: AuthContext | CurrentContext) -> WorkflowRun:
    workflow = db.scalar(
        select(WorkflowRun)
        .options(selectinload(WorkflowRun.nodes), selectinload(WorkflowRun.task))
        .where(WorkflowRun.workflow_id == workflow_id)
    )
    if workflow is None or workflow.task.organization_id != context.organization.organization_id:
        raise HTTPException(status_code=404, detail="workflow not found")
    return workflow


def _latest_workflow(db: Session, task: Task) -> WorkflowRun | None:
    return db.scalar(
        select(WorkflowRun)
        .options(selectinload(WorkflowRun.nodes))
        .where(WorkflowRun.task_id == task.task_id)
        .order_by(WorkflowRun.created_at.desc(), WorkflowRun.workflow_id.desc())
    )


def _dispatch_or_503(db: Session, workflow: WorkflowRun) -> WorkflowRun:
    try:
        dispatch_workflow(db, workflow)
    except Exception as exc:
        db.rollback()
        workflow = db.get(WorkflowRun, workflow.workflow_id)
        if workflow is not None:
            workflow.status = "failed"
            workflow.error_state = {"code": "WORKFLOW_DISPATCH_FAILED", "message": str(exc), "retryable": True}
            db.commit()
        raise HTTPException(status_code=503, detail="工作流未能提交到异步队列，请检查 Worker 和 Redis") from exc
    return workflow


@router.post("/tasks/{task_id}/workflow", response_model=WorkflowRead, status_code=status.HTTP_202_ACCEPTED)
def start_workflow(
    task_id: str,
    payload: WorkflowStartRequest,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> WorkflowRun:
    task = _get_task(db, task_id, context)
    params = payload.model_dump(exclude_none=True)
    workflow = create_workflow(db, task, actor_id=context.user.user_id, params=params)
    _dispatch_or_503(db, workflow)
    return _get_workflow(db, workflow.workflow_id, context)


@router.get("/tasks/{task_id}/workflow", response_model=WorkflowRead)
def get_task_workflow(task_id: str, context: CurrentContext, db: Session = Depends(get_db)) -> WorkflowRun:
    task = _get_task(db, task_id, context)
    workflow = _latest_workflow(db, task)
    if workflow is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return workflow


@router.get("/workflows/{workflow_id}", response_model=WorkflowRead)
def get_workflow(workflow_id: str, context: CurrentContext, db: Session = Depends(get_db)) -> WorkflowRun:
    return _get_workflow(db, workflow_id, context)


@router.post("/workflows/{workflow_id}/retry", response_model=WorkflowRead, status_code=status.HTTP_202_ACCEPTED)
def retry_failed_workflow(
    workflow_id: str,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> WorkflowRun:
    workflow = _get_workflow(db, workflow_id, context)
    try:
        retry_workflow(db, workflow, actor_id=context.user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _dispatch_or_503(db, workflow)
    return _get_workflow(db, workflow.workflow_id, context)


@router.post("/workflows/{workflow_id}/rerun", response_model=WorkflowRead, status_code=status.HTTP_202_ACCEPTED)
def rerun_workflow_node(
    workflow_id: str,
    payload: WorkflowRerunRequest,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> WorkflowRun:
    workflow = _get_workflow(db, workflow_id, context)
    try:
        new_workflow = create_node_rerun(db, workflow, actor_id=context.user.user_id, node_name=payload.node_name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _dispatch_or_503(db, new_workflow)
    return _get_workflow(db, new_workflow.workflow_id, context)
