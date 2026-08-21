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
from backend.app.services.regulation_ingest import parse_pdf


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
        raise HTTPException(status_code=415, detail="第九步当前只支持 PDF 法规原文")
    if suffix != ".pdf":
        raise HTTPException(status_code=415, detail="上传文件必须为 PDF")


@router.post("/regulations/import", response_model=RegulationImportRead, status_code=status.HTTP_201_CREATED)
async def import_regulation(
    file: UploadFile = File(...),
    task_id: str | None = Form(default=None),
    regulation_id: str | None = Form(default=None),
    version_label: str | None = Form(default=None),
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

    document_id = _id("DOC")
    settings = get_settings()
    storage_root = Path(settings.data_dir).expanduser() / "documents" / document_id
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_path = storage_root / _safe_name(file.filename or "regulation.pdf")
    storage_path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()

    try:
        parsed = parse_pdf(storage_path)
    except Exception as exc:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"PDF 解析失败：{exc}") from exc

    if task_id is not None:
        task = db.get(Task, task_id)
        if task is None or task.organization_id != context.organization.organization_id:
            raise HTTPException(status_code=404, detail="task not found")
    else:
        task = None

    document = SourceDocument(
        document_id=document_id,
        task_id=task_id,
        file_name=file.filename or storage_path.name,
        source_type="official_pdf",
        storage_key=str(storage_path.relative_to(Path(settings.data_dir).expanduser())),
        mime_type=file.content_type or "application/pdf",
        sha256=digest,
        page_count=parsed.page_count,
        source_url=source_url,
        document_metadata={
            "parse_status": "parsed",
            "parser": "pypdf",
            "title_detected": parsed.title,
            "warnings": parsed.warnings,
        },
    )

    regulation = db.get(Regulation, regulation_id) if regulation_id else None
    if regulation is None:
        regulation = Regulation(
            regulation_id=regulation_id or _id("REG"),
            title=parsed.title,
            document_no=parsed.document_no,
            issuer=parsed.issuer,
            document_type="法规原文",
            industry_scope=["金融业"],
            applicable_entities=[],
            status="effective" if parsed.effective_date else "unknown",
        )
        db.add(regulation)
    elif regulation.title != parsed.title and parsed.title:
        parsed_title = parsed.title
        regulation.title = regulation.title or parsed_title

    selected_version_label = version_label.strip() if version_label and version_label.strip() else parsed.version_label
    duplicate = db.scalar(
        select(RegulationVersion).where(
            RegulationVersion.regulation_id == regulation.regulation_id,
            RegulationVersion.version_label == selected_version_label,
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail=f"法规版本已登记：{selected_version_label}")

    previous_version_id: str | None = None
    current_version = db.scalar(
        select(RegulationVersion)
        .where(RegulationVersion.regulation_id == regulation.regulation_id, RegulationVersion.is_current.is_(True))
        .order_by(RegulationVersion.created_at.desc())
    )
    if current_version is not None:
        previous_version_id = current_version.version_id
        current_version.is_current = False

    version = RegulationVersion(
        version_id=_id("VER"),
        regulation=regulation,
        version_label=selected_version_label,
        publish_date=parsed.publish_date,
        effective_date=parsed.effective_date,
        status="effective" if parsed.effective_date else "unknown",
        source_document=document,
        previous_version_id=previous_version_id,
        source_sha256=digest,
        is_current=True,
    )
    db.add(version)
    db.flush()

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

    if task is not None:
        task.regulation_id = regulation.regulation_id
        task.source_document_ids = [*task.source_document_ids, document.document_id]
        task.current_step = "S1"
        task.task_status = "processing"
        task.step_status = {"S1": {"status": "completed", "article_count": len(articles), "page_count": parsed.page_count}}
    db.add(document)
    db.commit()
    db.refresh(document)
    db.refresh(regulation)
    db.refresh(version)

    sample = [ArticleRead.model_validate(article) for article in articles[:3]]
    return RegulationImportRead(
        source_document=document,
        regulation=regulation,
        version=version,
        article_count=len(articles),
        page_count=parsed.page_count,
        warnings=parsed.warnings,
        sample_articles=sample,
    )


@router.get("/regulations/{regulation_id}/versions/{version_id}/articles", response_model=list[ArticleRead])
def list_articles(
    regulation_id: str,
    version_id: str,
    context: AuthContext = Depends(require_roles("owner", "admin", "editor", "reviewer", "viewer")),
    db: Session = Depends(get_db),
) -> list[Article]:
    version = db.get(RegulationVersion, version_id)
    if version is None or version.regulation_id != regulation_id:
        raise HTTPException(status_code=404, detail="regulation version not found")
    return list(
        db.scalars(select(Article).where(Article.version_id == version_id).order_by(Article.article_order))
    )


@router.get("/articles/{article_id}", response_model=ArticleRead)
def get_article(
    article_id: str,
    context: AuthContext = Depends(require_roles("owner", "admin", "editor", "reviewer", "viewer")),
    db: Session = Depends(get_db),
) -> Article:
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="article not found")
    return article


@router.get("/source-documents/{document_id}/file")
def get_source_file(
    document_id: str,
    context: AuthContext = Depends(require_roles("owner", "admin", "editor", "reviewer", "viewer")),
    db: Session = Depends(get_db),
) -> FileResponse:
    document = db.get(SourceDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="source document not found")
    root = Path(get_settings().data_dir).expanduser().resolve()
    file_path = (root / document.storage_key).resolve()
    if root not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="source file not found")
    return FileResponse(file_path, media_type=document.mime_type or "application/pdf", filename=document.file_name)
