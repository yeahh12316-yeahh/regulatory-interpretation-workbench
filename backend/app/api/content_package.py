from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.schemas import ContentPackageRead
from backend.app.db.models import ContentPackage, Task
from backend.app.db.session import get_db
from backend.app.security import AuthContext, CurrentContext, require_roles
from backend.app.services.content_package_service import ContentPackageNotReady, create_locked_content_package


router = APIRouter(prefix="/api", tags=["content-package"])
EDIT_ROLES = ("owner", "admin", "editor", "reviewer")


def _get_task(db: Session, task_id: str, context: AuthContext) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.organization_id != context.organization.organization_id:
        raise HTTPException(status_code=404, detail="task not found")
    return task


def _read(package: ContentPackage) -> ContentPackageRead:
    return ContentPackageRead(
        package_id=package.package_id,
        task_id=package.task_id,
        regulation_id=package.regulation_id,
        pipeline_run_id=package.pipeline_run_id,
        package_version=package.package_version,
        status=package.status,
        content_hash=package.content_hash,
        content=package.content_json,
        created_by=package.created_by,
        locked_by=package.locked_by,
        locked_at=package.locked_at,
        created_at=package.created_at,
    )


@router.post("/tasks/{task_id}/content-package", response_model=ContentPackageRead, status_code=status.HTTP_201_CREATED)
def create_content_package(
    task_id: str,
    context: AuthContext = Depends(require_roles(*EDIT_ROLES)),
    db: Session = Depends(get_db),
) -> ContentPackageRead:
    task = _get_task(db, task_id, context)
    try:
        package = create_locked_content_package(db, task, actor_id=context.user.user_id)
    except ContentPackageNotReady as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"message": str(exc), "missing": exc.missing}) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(package)
    return _read(package)


@router.get("/tasks/{task_id}/content-package", response_model=ContentPackageRead)
def get_content_package(task_id: str, context: CurrentContext, db: Session = Depends(get_db)) -> ContentPackageRead:
    task = _get_task(db, task_id, context)
    package = db.scalar(select(ContentPackage).where(ContentPackage.task_id == task.task_id).order_by(ContentPackage.package_version.desc()))
    if package is None:
        raise HTTPException(status_code=404, detail="Content Package 尚未生成")
    return _read(package)
