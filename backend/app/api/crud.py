from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.schemas import (
    EvidenceCreate,
    EvidenceRead,
    RegulationCreate,
    RegulationRead,
    SourceDocumentCreate,
    SourceDocumentRead,
    TaskCreate,
    TaskRead,
)
from backend.app.db.models import Evidence, Regulation, SourceDocument, Task
from backend.app.db.session import get_db


router = APIRouter(prefix="/api", tags=["data"])


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _get_or_404(db: Session, model, object_id: str, label: str):
    item = db.get(model, object_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{label} not found: {object_id}")
    return item


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    if payload.regulation_id is not None:
        _get_or_404(db, Regulation, payload.regulation_id, "regulation")
    task = Task(
        task_id=payload.task_id or _id("TASK"),
        task_name=payload.task_name,
        created_by=payload.created_by,
        regulation_id=payload.regulation_id,
        processing_config=payload.processing_config,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: str, db: Session = Depends(get_db)) -> Task:
    return _get_or_404(db, Task, task_id, "task")


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(limit: int = 50, db: Session = Depends(get_db)) -> list[Task]:
    return list(db.scalars(select(Task).order_by(Task.created_at.desc()).limit(min(limit, 200))))


@router.post("/regulations", response_model=RegulationRead, status_code=status.HTTP_201_CREATED)
def create_regulation(payload: RegulationCreate, db: Session = Depends(get_db)) -> Regulation:
    regulation = Regulation(
        regulation_id=payload.regulation_id or _id("REG"),
        title=payload.title,
        document_no=payload.document_no,
        issuer=payload.issuer,
        document_type=payload.document_type,
        industry_scope=payload.industry_scope,
        applicable_entities=payload.applicable_entities,
        status=payload.status,
    )
    db.add(regulation)
    db.commit()
    db.refresh(regulation)
    return regulation


@router.get("/regulations/{regulation_id}", response_model=RegulationRead)
def get_regulation(regulation_id: str, db: Session = Depends(get_db)) -> Regulation:
    return _get_or_404(db, Regulation, regulation_id, "regulation")


@router.get("/regulations", response_model=list[RegulationRead])
def list_regulations(limit: int = 50, db: Session = Depends(get_db)) -> list[Regulation]:
    return list(db.scalars(select(Regulation).order_by(Regulation.created_at.desc()).limit(min(limit, 200))))


@router.post("/source-documents", response_model=SourceDocumentRead, status_code=status.HTTP_201_CREATED)
def create_source_document(payload: SourceDocumentCreate, db: Session = Depends(get_db)) -> SourceDocument:
    if payload.task_id is not None:
        _get_or_404(db, Task, payload.task_id, "task")
    document = SourceDocument(
        document_id=payload.document_id or _id("DOC"),
        task_id=payload.task_id,
        file_name=payload.file_name,
        source_type=payload.source_type,
        storage_key=payload.storage_key,
        mime_type=payload.mime_type,
        sha256=payload.sha256,
        page_count=payload.page_count,
        source_url=payload.source_url,
        document_metadata=payload.document_metadata,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/source-documents/{document_id}", response_model=SourceDocumentRead)
def get_source_document(document_id: str, db: Session = Depends(get_db)) -> SourceDocument:
    return _get_or_404(db, SourceDocument, document_id, "source document")


@router.post("/evidence", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db)) -> Evidence:
    _get_or_404(db, SourceDocument, payload.source_document_id, "source document")
    if payload.task_id is not None:
        _get_or_404(db, Task, payload.task_id, "task")
    if payload.regulation_id is not None:
        _get_or_404(db, Regulation, payload.regulation_id, "regulation")
    evidence = Evidence(
        evidence_id=payload.evidence_id or _id("EVID"),
        task_id=payload.task_id,
        regulation_id=payload.regulation_id,
        article_id=payload.article_id,
        source_document_id=payload.source_document_id,
        source_type=payload.source_type,
        locator=payload.locator,
        source_text=payload.source_text,
        description=payload.description,
        source_url=payload.source_url,
        verification_status=payload.verification_status,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/evidence/{evidence_id}", response_model=EvidenceRead)
def get_evidence(evidence_id: str, db: Session = Depends(get_db)) -> Evidence:
    return _get_or_404(db, Evidence, evidence_id, "evidence")


@router.get("/evidence", response_model=list[EvidenceRead])
def list_evidence(limit: int = 50, db: Session = Depends(get_db)) -> list[Evidence]:
    return list(db.scalars(select(Evidence).order_by(Evidence.created_at.desc()).limit(min(limit, 200))))
