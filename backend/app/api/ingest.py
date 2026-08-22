from __future__ import annotations

import hashlib
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.schemas import ArticleRead, RegulationImportRead
from backend.app.core.config import get_settings
from backend.app.db.models import Article, Regulation, RegulationVersion, SourceDocument, Task
from backend.app.db.session import get_db
from backend.app.security import AuthContext, require_roles
from backend.app.services.regulation_ingest import ParsedRegulation, parse_pdf


router = APIRouter(prefix="/api", tags=["regulation-ingest"])
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _safe_name(file_name: str) -> str:
    name = Path(file_name or "regulation.pdf").name
    return re.sub(r"[^\w.\-\u4e00-\u9fff（）()【】《》]+", "_", name)[:180] or "regulation.pdf"


def _check_pdf(file: UploadFile) -> None:
    suffix = Path(file.filename or "").suffix.lower()
    if file.content_type not in {None, "", "application/pdf", "application/octet-stream"} and suffix != ".pdf":
        raise HTTPException(status_code=415, detail="法规上传当前只支持 PDF 原文")
    if suffix != ".pdf":
        raise HTTPException(status_code=415, detail="上传文件必须为 PDF")


def _document_path(document: SourceDocument) -> Path:
    root = Path(get_settings().data_dir).expanduser().resolve()
    path = (root / document.storage_key).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="source file not found")
    return path


def _parsed_metadata(parsed: ParsedRegulation, *, parser_status: str = "parsed") -> dict[str, object]:
    return {
        "parse_status": parser_status,
        "parser": "pypdf+ocr" if parsed.extraction_summary.get("ocr_pages") else "pypdf",
        "title_detected": parsed.title,
        "warnings": parsed.warnings,
        "extraction_summary": parsed.extraction_summary,
    }


def _complete_import(
    *,
    db: Session,
    document: SourceDocument,
    parsed: ParsedRegulation,
    regulation_id: str | None,
    version_label: str | None,
    version_role: str,
) -> RegulationImportRead:
    task = db.get(Task, document.task_id) if document.task_id else None
    if task is None:
        raise HTTPException(status_code=404, detail="task not found for source document")

    regulation = db.get(Regulation, regulation_id) if regulation_id else None
    if regulation is not None and regulation.organization_id != task.organization_id:
        raise HTTPException(status_code=404, detail="regulation not found")
    if regulation is None:
        regulation = Regulation(
            regulation_id=regulation_id or _id("REG"),
            organization_id=task.organization_id,
            title=parsed.title,
            document_no=parsed.document_no,
            issuer=parsed.issuer,
            document_type="法规原文",
            industry_scope=["金融业"],
            applicable_entities=[],
            status="effective" if parsed.effective_date else "unknown",
        )
        db.add(regulation)
    elif parsed.title and not regulation.title:
        regulation.title = parsed.title

    selected_version_label = version_label.strip() if version_label and version_label.strip() else parsed.version_label
    duplicate = db.scalar(
        select(RegulationVersion).where(
            RegulationVersion.regulation_id == regulation.regulation_id,
            RegulationVersion.version_label == selected_version_label,
        )
    )
    if duplicate is not None:
        document.document_metadata = {
            **document.document_metadata,
            "parse_status": "rejected_duplicate_version",
            "duplicate_version_id": duplicate.version_id,
        }
        db.commit()
        raise HTTPException(status_code=409, detail=f"法规版本已登记：{selected_version_label}")

    current_version = db.scalar(
        select(RegulationVersion)
        .where(RegulationVersion.regulation_id == regulation.regulation_id, RegulationVersion.is_current.is_(True))
        .order_by(RegulationVersion.created_at.desc())
    )
    if version_role not in {"current", "previous"}:
        raise HTTPException(status_code=422, detail="version_role 只能为 current 或 previous")
    if version_role == "previous" and current_version is None:
        raise HTTPException(status_code=409, detail="补充旧规版本前，当前法规必须已有一个已登记版本")

    previous_version_id: str | None = None
    is_current = version_role == "current"
    if current_version is not None and version_role == "current":
        previous_version_id = current_version.version_id
        current_version.is_current = False
    elif current_version is not None and version_role == "previous":
        previous_version_id = current_version.previous_version_id

    document.page_count = parsed.page_count
    document.document_metadata = {
        **document.document_metadata,
        **_parsed_metadata(parsed),
    }
    version = RegulationVersion(
        version_id=_id("VER"),
        regulation=regulation,
        version_label=selected_version_label,
        publish_date=parsed.publish_date,
        effective_date=parsed.effective_date,
        status="effective" if parsed.effective_date else "unknown",
        source_document=document,
        previous_version_id=previous_version_id,
        source_sha256=document.sha256,
        is_current=is_current,
    )
    db.add(version)
    db.flush()
    if current_version is not None and version_role == "previous":
        current_version.previous_version_id = version.version_id

    articles: list[Article] = []
    for parsed_article in parsed.articles:
        article = Article(
            article_id=f"{version.version_id}_ART_{parsed_article.article_order:03d}",
            version_id=version.version_id,
            article_no=parsed_article.article_no,
            chapter_no=parsed_article.chapter_no,
            article_order=parsed_article.article_order,
            original_text=parsed_article.original_text,
            source_page=parsed_article.source_page,
            source_offset=parsed_article.source_offset,
        )
        articles.append(article)
        db.add(article)

    task.regulation_id = regulation.regulation_id
    if document.document_id not in task.source_document_ids:
        task.source_document_ids = [*task.source_document_ids, document.document_id]
    task.current_step = "S1"
    task.task_status = "processing"
    task.error_state = {}
    task.last_checkpoint = {
        "stage": "regulation_ingest",
        "document_id": document.document_id,
        "article_count": len(articles),
        "page_count": parsed.page_count,
        "version_role": version_role,
    }
    task.step_status = {
        **task.step_status,
        "S1": {"status": "completed", "article_count": len(articles), "page_count": parsed.page_count},
    }
    db.commit()
    db.refresh(document)
    db.refresh(regulation)
    db.refresh(version)

    return RegulationImportRead(
        task_id=task.task_id,
        source_document=document,
        regulation=regulation,
        version=version,
        article_count=len(articles),
        page_count=parsed.page_count,
        warnings=parsed.warnings,
        sample_articles=[ArticleRead.model_validate(article) for article in articles[:3]],
    )


def _import_read_for_document(db: Session, document: SourceDocument) -> RegulationImportRead:
    task = db.get(Task, document.task_id) if document.task_id else None
    version = db.scalar(select(RegulationVersion).where(RegulationVersion.source_document_id == document.document_id))
    if task is None or version is None:
        raise HTTPException(status_code=404, detail="source document import record not found")
    regulation = db.get(Regulation, version.regulation_id)
    if regulation is None:
        raise HTTPException(status_code=404, detail="regulation import record not found")
    articles = list(db.scalars(select(Article).where(Article.version_id == version.version_id).order_by(Article.article_order)))
    return RegulationImportRead(
        task_id=task.task_id,
        source_document=document,
        regulation=regulation,
        version=version,
        article_count=len(articles),
        page_count=document.page_count or 0,
        warnings=list(document.document_metadata.get("warnings") or []),
        sample_articles=[ArticleRead.model_validate(article) for article in articles[:3]],
    )


def _mark_parse_failed(db: Session, document_id: str, error: str, *, attempt: int) -> None:
    document = db.get(SourceDocument, document_id)
    if document is None:
        return
    document.document_metadata = {
        **document.document_metadata,
        "parse_status": "failed",
        "parser_error": error,
        "retryable": True,
        "parse_attempts": attempt,
    }
    document.page_count = None
    if document.task_id:
        task = db.get(Task, document.task_id)
        if task is not None:
            task.task_status = "failed"
            task.error_state = {
                "stage": "regulation_ingest",
                "document_id": document_id,
                "message": error,
                "retryable": True,
            }
            task.last_checkpoint = {"stage": "upload_persisted_parse_failed", "document_id": document_id}
    db.commit()


async def _parse_uploaded_document(
    *,
    db: Session,
    document_id: str,
    path: Path,
    regulation_id: str | None,
    version_label: str | None,
    version_role: str,
    attempt: int,
) -> RegulationImportRead:
    settings = get_settings()
    try:
        parsed = parse_pdf(path, enable_ocr=settings.enable_ocr_fallback)
    except Exception as exc:
        message = f"PDF 解析失败：{exc}"
        _mark_parse_failed(db, document_id, message, attempt=attempt)
        raise HTTPException(
            status_code=422,
            detail={
                "message": message,
                "document_id": document_id,
                "retryable": True,
                "retry_url": f"/api/source-documents/{document_id}/retry-parse",
            },
        ) from exc

    if not parsed.articles:
        warning_text = "；".join(parsed.warnings) or "未识别到以‘第×条’开头的条款"
        message = f"PDF 解析未形成可登记条款：{warning_text}"
        _mark_parse_failed(db, document_id, message, attempt=attempt)
        raise HTTPException(
            status_code=422,
            detail={
                "message": message,
                "document_id": document_id,
                "retryable": True,
                "retry_url": f"/api/source-documents/{document_id}/retry-parse",
            },
        )

    document = db.get(SourceDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="source document not found")
    return _complete_import(
        db=db,
        document=document,
        parsed=parsed,
        regulation_id=regulation_id,
        version_label=version_label,
        version_role=version_role,
    )


@router.post("/regulations/import", response_model=RegulationImportRead, status_code=status.HTTP_201_CREATED)
async def import_regulation(
    file: UploadFile = File(...),
    task_id: str | None = Form(default=None),
    regulation_id: str | None = Form(default=None),
    version_label: str | None = Form(default=None),
    version_role: str = Form(default="current"),
    upload_id: str | None = Form(default=None),
    source_url: str | None = Form(default=None),
    context: AuthContext = Depends(require_roles("owner", "admin", "editor")),
    db: Session = Depends(get_db),
) -> RegulationImportRead:
    _check_pdf(file)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="上传文件为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="单个 PDF 不能超过 25 MB")

    if version_role not in {"current", "previous"}:
        raise HTTPException(status_code=422, detail="version_role 只能为 current 或 previous")

    if upload_id:
        existing_document = next(
            (
                candidate
                for candidate in db.scalars(
                    select(SourceDocument).join(Task, Task.task_id == SourceDocument.task_id).where(
                        Task.organization_id == context.organization.organization_id
                    )
                )
                if candidate.document_metadata.get("upload_id") == upload_id
            ),
            None,
        )
        if existing_document is not None:
            parse_status = existing_document.document_metadata.get("parse_status")
            if parse_status == "parsed":
                return _import_read_for_document(db, existing_document)
            path = _document_path(existing_document)
            existing_task = db.get(Task, existing_document.task_id)
            if existing_task is None:
                raise HTTPException(status_code=404, detail="source document task not found")
            attempts = int(existing_document.document_metadata.get("parse_attempts", 0)) + 1
            existing_document.document_metadata = {
                **existing_document.document_metadata,
                "parse_status": "retrying",
                "parse_attempts": attempts,
            }
            existing_task.task_status = "uploading"
            db.commit()
            return await _parse_uploaded_document(
                db=db,
                document_id=existing_document.document_id,
                path=path,
                regulation_id=existing_document.document_metadata.get("requested_regulation_id"),
                version_label=existing_document.document_metadata.get("requested_version_label"),
                version_role=existing_document.document_metadata.get("version_role", "current"),
                attempt=attempts,
            )

    if task_id is not None:
        task = db.get(Task, task_id)
        if task is None or task.organization_id != context.organization.organization_id:
            raise HTTPException(status_code=404, detail="task not found")
    else:
        task = Task(
            task_id=_id("TASK"),
            task_name=f"{Path(file.filename or '法规').stem} 解读",
            created_by=context.user.email,
            organization_id=context.organization.organization_id,
            owner_id=context.user.user_id,
            task_status="uploading",
        )
        db.add(task)
        db.flush()
        task_id = task.task_id

    document_id = _id("DOC")
    settings = get_settings()
    data_root = Path(settings.data_dir).expanduser()
    storage_root = data_root / "documents" / document_id
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_path = storage_root / _safe_name(file.filename or "regulation.pdf")
    storage_path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()

    document = SourceDocument(
        document_id=document_id,
        task_id=task_id,
        file_name=file.filename or storage_path.name,
        source_type="official_pdf",
        storage_key=str(storage_path.relative_to(data_root)),
        mime_type=file.content_type or "application/pdf",
        sha256=digest,
        page_count=None,
        source_url=source_url,
        document_metadata={
            "parse_status": "uploaded",
            "retryable": True,
            "parse_attempts": 0,
            "requested_regulation_id": regulation_id,
            "requested_version_label": version_label,
            "version_role": version_role,
            "upload_id": upload_id,
        },
    )
    db.add(document)
    if document_id not in task.source_document_ids:
        task.source_document_ids = [*task.source_document_ids, document_id]
    task.last_checkpoint = {"stage": "upload_persisted", "document_id": document_id}
    db.commit()

    return await _parse_uploaded_document(
        db=db,
        document_id=document_id,
        path=storage_path,
        regulation_id=regulation_id,
        version_label=version_label,
        version_role=version_role,
        attempt=1,
    )


@router.post("/source-documents/{document_id}/retry-parse", response_model=RegulationImportRead, status_code=status.HTTP_201_CREATED)
async def retry_parse(
    document_id: str,
    context: AuthContext = Depends(require_roles("owner", "admin", "editor")),
    db: Session = Depends(get_db),
) -> RegulationImportRead:
    document = db.get(SourceDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="source document not found")
    task = db.get(Task, document.task_id) if document.task_id else None
    if task is None or task.organization_id != context.organization.organization_id:
        raise HTTPException(status_code=404, detail="source document not found")
    if document.document_metadata.get("parse_status") == "parsed":
        raise HTTPException(status_code=409, detail="该来源文件已经解析成功，无需重复重试")

    path = _document_path(document)
    attempts = int(document.document_metadata.get("parse_attempts", 0)) + 1
    document.document_metadata = {
        **document.document_metadata,
        "parse_status": "retrying",
        "parse_attempts": attempts,
    }
    task.task_status = "uploading"
    db.commit()
    return await _parse_uploaded_document(
        db=db,
        document_id=document_id,
        path=path,
        regulation_id=document.document_metadata.get("requested_regulation_id"),
        version_label=document.document_metadata.get("requested_version_label"),
        version_role=document.document_metadata.get("version_role", "current"),
        attempt=attempts,
    )


@router.get("/regulations/{regulation_id}/versions/{version_id}/articles", response_model=list[ArticleRead])
def list_articles(
    regulation_id: str,
    version_id: str,
    context: AuthContext = Depends(require_roles("owner", "admin", "editor", "reviewer", "viewer")),
    db: Session = Depends(get_db),
) -> list[Article]:
    version = db.get(RegulationVersion, version_id)
    if version is None or version.regulation_id != regulation_id or version.regulation.organization_id != context.organization.organization_id:
        raise HTTPException(status_code=404, detail="regulation version not found")
    return list(db.scalars(select(Article).where(Article.version_id == version_id).order_by(Article.article_order)))


@router.get("/articles/{article_id}", response_model=ArticleRead)
def get_article(
    article_id: str,
    context: AuthContext = Depends(require_roles("owner", "admin", "editor", "reviewer", "viewer")),
    db: Session = Depends(get_db),
) -> Article:
    article = db.get(Article, article_id)
    if article is None or article.version.regulation.organization_id != context.organization.organization_id:
        raise HTTPException(status_code=404, detail="article not found")
    return article


@router.get("/source-documents/{document_id}/file")
def get_source_file(
    document_id: str,
    context: AuthContext = Depends(require_roles("owner", "admin", "editor", "reviewer", "viewer")),
    db: Session = Depends(get_db),
) -> FileResponse:
    document = db.get(SourceDocument, document_id)
    if document is None or document.task is None or document.task.organization_id != context.organization.organization_id:
        raise HTTPException(status_code=404, detail="source document not found")
    file_path = _document_path(document)
    return FileResponse(file_path, media_type=document.mime_type or "application/pdf", filename=document.file_name)
