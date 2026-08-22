from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.schemas import (
    EvidenceRead,
    InterpretationRead,
    PipelineRunRead,
    PipelineRunRequest,
    RequirementRead,
    TaskRead,
)
from backend.app.db.models import Evidence, Interpretation, Requirement, Task
from backend.app.db.session import get_db
from backend.app.security import AuthContext, CurrentContext, require_roles
from backend.app.services.interpretation_pipeline import run_s1_s4_pipeline
from backend.app.services.result_ordering import order_article_records


router = APIRouter(prefix="/api", tags=["interpretation-pipeline"])


def _get_task(db: Session, task_id: str, context: AuthContext) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.organization_id != context.organization.organization_id:
        raise HTTPException(status_code=404, detail="task not found")
    return task


def _latest_run_id(task: Task) -> str | None:
    value = (task.step_status or {}).get("pipeline_run_id")
    return value if isinstance(value, str) and value else None


def _read_result(db: Session, task: Task) -> PipelineRunRead:
    run_id = _latest_run_id(task)
    if not run_id:
        raise HTTPException(status_code=404, detail="S1-S4 尚未运行")
    interpretations = list(
        db.scalars(
            select(Interpretation)
            .where(Interpretation.regulation_id == task.regulation_id, Interpretation.pipeline_run_id == run_id)
            .order_by(Interpretation.article_id.is_not(None), Interpretation.created_at, Interpretation.interpretation_id)
        )
    )
    overall = next((item for item in interpretations if item.article_id is None), None)
    if overall is None:
        raise HTTPException(status_code=409, detail="S4结果缺少整体解读")
    article_interpretations = order_article_records([item for item in interpretations if item.article_id is not None])
    requirements = order_article_records(list(
        db.scalars(
            select(Requirement)
            .where(Requirement.pipeline_run_id == run_id)
            .order_by(Requirement.article_id, Requirement.requirement_id)
        )
    ))
    linked_evidence_ids = {
        evidence.evidence_id
        for interpretation in [overall, *article_interpretations]
        for evidence in interpretation.evidence
    }
    evidence = list(
        db.scalars(
            select(Evidence)
            .where(Evidence.task_id == task.task_id, Evidence.evidence_id.in_(linked_evidence_ids))
            .order_by(Evidence.created_at, Evidence.evidence_id)
        )
    ) if linked_evidence_ids else []
    return PipelineRunRead(
        pipeline_run_id=run_id,
        pipeline_version=task.processing_config.get("pipeline_version", "s1-s4-rule-based-v1"),
        task=TaskRead.model_validate(task),
        stages=task.step_status,
        overall=InterpretationRead.model_validate(overall),
        article_interpretations=[InterpretationRead.model_validate(item) for item in article_interpretations],
        requirements=[RequirementRead.model_validate(item) for item in requirements],
        evidence=[EvidenceRead.model_validate(item) for item in evidence],
    )


@router.post("/tasks/{task_id}/interpret", response_model=PipelineRunRead, status_code=status.HTTP_200_OK)
def run_interpretation_pipeline(
    task_id: str,
    payload: PipelineRunRequest,
    context: AuthContext = Depends(require_roles("owner", "admin", "editor")),
    db: Session = Depends(get_db),
) -> PipelineRunRead:
    task = _get_task(db, task_id, context)
    try:
        run_s1_s4_pipeline(
            db,
            task,
            institution_type=payload.institution_type,
            business_scope=payload.business_scope,
            region=payload.region,
            interpretation_as_of=payload.interpretation_as_of,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _read_result(db, task)


@router.get("/tasks/{task_id}/interpretation", response_model=PipelineRunRead)
def get_interpretation_pipeline(
    task_id: str,
    context: CurrentContext,
    db: Session = Depends(get_db),
) -> PipelineRunRead:
    task = _get_task(db, task_id, context)
    return _read_result(db, task)


@router.get("/tasks/{task_id}/requirements", response_model=list[RequirementRead])
def list_pipeline_requirements(
    task_id: str,
    context: CurrentContext,
    db: Session = Depends(get_db),
) -> list[Requirement]:
    task = _get_task(db, task_id, context)
    run_id = _latest_run_id(task)
    if not run_id:
        raise HTTPException(status_code=404, detail="S1-S4 尚未运行")
    return order_article_records(list(
        db.scalars(
            select(Requirement).where(Requirement.pipeline_run_id == run_id).order_by(Requirement.article_id, Requirement.requirement_id)
        )
    ))
