from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    task_id: str | None = Field(default=None, max_length=64)
    task_name: str = Field(min_length=1, max_length=255)
    created_by: str = Field(min_length=1, max_length=128)
    regulation_id: str | None = Field(default=None, max_length=64)
    processing_config: dict[str, Any] = Field(default_factory=dict)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    task_name: str
    created_by: str
    current_step: str
    task_status: str
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
