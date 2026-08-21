from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    task_id: str | None = Field(default=None, max_length=64)
    task_name: str = Field(min_length=1, max_length=255)
    created_by: str | None = Field(default=None, max_length=128)
    regulation_id: str | None = Field(default=None, max_length=64)
    processing_config: dict[str, Any] = Field(default_factory=dict)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    task_name: str
    created_by: str
    current_step: str
    task_status: str
    organization_id: str | None
    owner_id: str | None
    regulation_id: str | None
    source_document_ids: list[str]
    processing_config: dict[str, Any]
    step_status: dict[str, Any]
    error_state: dict[str, Any]
    last_checkpoint: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RegulationCreate(BaseModel):
    regulation_id: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=1, max_length=512)
    document_no: str | None = Field(default=None, max_length=128)
    issuer: list[str] = Field(default_factory=list)
    document_type: str | None = Field(default=None, max_length=128)
    industry_scope: list[str] = Field(default_factory=list)
    applicable_entities: list[str] = Field(default_factory=list)
    status: str = Field(default="effective", max_length=32)


class RegulationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    regulation_id: str
    title: str
    document_no: str | None
    issuer: list[str]
    document_type: str | None
    industry_scope: list[str]
    applicable_entities: list[str]
    status: str
    created_at: datetime


class SourceDocumentCreate(BaseModel):
    document_id: str | None = Field(default=None, max_length=64)
    task_id: str | None = Field(default=None, max_length=64)
    file_name: str = Field(min_length=1, max_length=512)
    source_type: str = Field(min_length=1, max_length=64)
    storage_key: str = Field(min_length=1, max_length=1024)
    mime_type: str | None = Field(default=None, max_length=128)
    sha256: str = Field(min_length=64, max_length=64)
    page_count: int | None = Field(default=None, ge=1)
    source_url: str | None = Field(default=None, max_length=2048)
    document_metadata: dict[str, Any] = Field(default_factory=dict)


class SourceDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    task_id: str | None
    file_name: str
    source_type: str
    storage_key: str
    mime_type: str | None
    sha256: str
    page_count: int | None
    source_url: str | None
    document_metadata: dict[str, Any]
    created_at: datetime


class EvidenceCreate(BaseModel):
    evidence_id: str | None = Field(default=None, max_length=96)
    task_id: str | None = Field(default=None, max_length=64)
    regulation_id: str | None = Field(default=None, max_length=64)
    article_id: str | None = Field(default=None, max_length=96)
    source_document_id: str = Field(max_length=64)
    source_type: str = Field(min_length=1, max_length=64)
    locator: dict[str, Any] = Field(default_factory=dict)
    source_text: str | None = None
    description: str | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    verification_status: str = Field(default="unverified", max_length=32)


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: str
    task_id: str | None
    regulation_id: str | None
    article_id: str | None
    source_document_id: str
    source_type: str
    locator: dict[str, Any]
    source_text: str | None
    description: str | None
    source_url: str | None
    verification_status: str
    created_at: datetime


class RegulationVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: str
    regulation_id: str
    version_label: str
    publish_date: date | None
    effective_date: date | None
    abolish_date: date | None
    status: str
    source_document_id: str
    previous_version_id: str | None
    source_sha256: str
    is_current: bool
    created_at: datetime


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    article_id: str
    version_id: str
    article_no: str
    chapter_no: str | None
    article_order: int
    original_text: str
    source_page: int | None
    source_offset: dict[str, Any]
    article_type: list[str]
    interpretation_status: str


class RegulationImportRead(BaseModel):
    task_id: str | None = None
    source_document: SourceDocumentRead
    regulation: RegulationRead
    version: RegulationVersionRead
    article_count: int
    page_count: int
    warnings: list[str]
    sample_articles: list[ArticleRead]


class PipelineRunRequest(BaseModel):
    institution_type: str = Field(default="商业银行", min_length=1, max_length=128)
    business_scope: list[str] = Field(default_factory=list)
    region: str | None = Field(default="中国境内", max_length=128)
    interpretation_as_of: str | None = Field(default=None, max_length=32)


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requirement_id: str
    article_id: str
    subject: str | None
    rule_type: str
    action: str | None
    object: str | None
    condition: str | None
    deadline: str | None
    frequency: str | None
    threshold: str | None
    exception: str | None
    evidence_required: str | None
    related_articles: list[str]
    source_text: str
    confidence: float | None
    fact_class: str
    review_status: str
    structured_data: dict[str, Any]
    pipeline_run_id: str | None


class InterpretationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    interpretation_id: str
    regulation_id: str
    article_id: str | None
    summary: str | None
    interpretation: str | None
    regulatory_meaning: str | None
    key_points: list[str]
    conditions: list[str]
    exceptions: list[str]
    linked_requirements: list[str]
    content_type: str
    confidence: float | None
    review_status: str
    fact_class: str
    content_blocks: list[dict[str, Any]]
    generated_by: str
    prompt_version: str | None
    human_lock: bool
    content_version: int
    pipeline_run_id: str | None


class PipelineStageRead(BaseModel):
    status: str
    version: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class PipelineRunRead(BaseModel):
    pipeline_run_id: str
    pipeline_version: str
    task: TaskRead
    stages: dict[str, Any]
    overall: InterpretationRead
    article_interpretations: list[InterpretationRead]
    requirements: list[RequirementRead]
    evidence: list[EvidenceRead]
