from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


JsonType = JSON


def json_column(default: Any = dict) -> Mapped[dict[str, Any]]:
    return mapped_column(JsonType, default=default, nullable=False)


interpretation_evidence = Table(
    "interpretation_evidence",
    Base.metadata,
    Column("interpretation_id", ForeignKey("interpretations.interpretation_id", ondelete="CASCADE"), primary_key=True),
    Column("evidence_id", ForeignKey("evidence.evidence_id", ondelete="CASCADE"), primary_key=True),
)


requirement_evidence = Table(
    "requirement_evidence",
    Base.metadata,
    Column("requirement_id", ForeignKey("requirements.requirement_id", ondelete="CASCADE"), primary_key=True),
    Column("evidence_id", ForeignKey("evidence.evidence_id", ondelete="CASCADE"), primary_key=True),
)


class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    current_step: Mapped[str] = mapped_column(String(32), default="INPUT", nullable=False)
    task_status: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.organization_id", ondelete="SET NULL"), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    regulation_id: Mapped[str | None] = mapped_column(ForeignKey("regulations.regulation_id"), nullable=True)
    source_document_ids: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    processing_config: Mapped[dict[str, Any]] = json_column()
    step_status: Mapped[dict[str, Any]] = json_column()
    error_state: Mapped[dict[str, Any]] = json_column()
    last_checkpoint: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    source_documents: Mapped[list[SourceDocument]] = relationship(back_populates="task")
    organization: Mapped[Organization | None] = relationship(back_populates="tasks")
    owner: Mapped[User | None] = relationship(back_populates="owned_tasks")
    regulation: Mapped[Regulation | None] = relationship(back_populates="tasks", foreign_keys=[regulation_id])
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="task")
    qc_results: Mapped[list[QCResult]] = relationship(back_populates="task")
    content_packages: Mapped[list[ContentPackage]] = relationship(back_populates="task")
    workflow_runs: Mapped[list[WorkflowRun]] = relationship(back_populates="task", cascade="all, delete-orphan")


class Organization(Base):
    __tablename__ = "organizations"

    organization_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tasks: Mapped[list[Task]] = relationship(back_populates="organization")
    regulations: Mapped[list[Regulation]] = relationship(back_populates="organization")
    members: Mapped[list[OrganizationMember]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    memberships: Mapped[list[OrganizationMember]] = relationship(back_populates="user", cascade="all, delete-orphan")
    owned_tasks: Mapped[list[Task]] = relationship(back_populates="owner")


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    member_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="viewer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")

    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_organization_member"),)


class SourceDocument(Base):
    __tablename__ = "source_documents"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.task_id", ondelete="SET NULL"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    document_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JsonType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[Task | None] = relationship(back_populates="source_documents")
    versions: Mapped[list[RegulationVersion]] = relationship(back_populates="source_document")
    evidence: Mapped[list[Evidence]] = relationship(back_populates="source_document")

    __table_args__ = (Index("ix_source_documents_sha256", "sha256"),)


class Regulation(Base):
    __tablename__ = "regulations"

    regulation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.organization_id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    document_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issuer: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    industry_scope: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    applicable_entities: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="effective", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tasks: Mapped[list[Task]] = relationship(back_populates="regulation", foreign_keys=[Task.regulation_id])
    organization: Mapped[Organization | None] = relationship(back_populates="regulations")
    versions: Mapped[list[RegulationVersion]] = relationship(back_populates="regulation", foreign_keys="RegulationVersion.regulation_id")
    evidence: Mapped[list[Evidence]] = relationship(back_populates="regulation")
    interpretations: Mapped[list[Interpretation]] = relationship(back_populates="regulation")
    version_relations: Mapped[list[VersionRelation]] = relationship(back_populates="regulation", foreign_keys="VersionRelation.regulation_id")
    content_packages: Mapped[list[ContentPackage]] = relationship(back_populates="regulation")


class RegulationVersion(Base):
    __tablename__ = "regulation_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    regulation_id: Mapped[str] = mapped_column(ForeignKey("regulations.regulation_id", ondelete="CASCADE"), nullable=False)
    version_label: Mapped[str] = mapped_column(String(128), nullable=False)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    abolish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="effective", nullable=False)
    source_document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.document_id"), nullable=False)
    previous_version_id: Mapped[str | None] = mapped_column(ForeignKey("regulation_versions.version_id"), nullable=True)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    regulation: Mapped[Regulation] = relationship(back_populates="versions", foreign_keys=[regulation_id])
    source_document: Mapped[SourceDocument] = relationship(back_populates="versions")
    previous_version: Mapped[RegulationVersion | None] = relationship(remote_side=[version_id])
    articles: Mapped[list[Article]] = relationship(back_populates="version")
    from_relations: Mapped[list[VersionRelation]] = relationship(back_populates="from_version", foreign_keys="VersionRelation.from_version_id")
    to_relations: Mapped[list[VersionRelation]] = relationship(back_populates="to_version", foreign_keys="VersionRelation.to_version_id")

    __table_args__ = (
        UniqueConstraint("regulation_id", "version_label", name="uq_regulation_version_label"),
        Index("ix_regulation_versions_sha256", "source_sha256"),
    )


class Article(Base):
    __tablename__ = "articles"

    article_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("regulation_versions.version_id", ondelete="CASCADE"), nullable=False)
    article_no: Mapped[str] = mapped_column(String(64), nullable=False)
    chapter_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    article_order: Mapped[int] = mapped_column(Integer, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_offset: Mapped[dict[str, Any]] = json_column()
    article_type: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    interpretation_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)

    version: Mapped[RegulationVersion] = relationship(back_populates="articles")
    requirements: Mapped[list[Requirement]] = relationship(back_populates="article")
    interpretations: Mapped[list[Interpretation]] = relationship(back_populates="article")
    evidence: Mapped[list[Evidence]] = relationship(back_populates="article")

    __table_args__ = (UniqueConstraint("version_id", "article_order", name="uq_article_order_per_version"),)


class Requirement(Base):
    __tablename__ = "requirements"

    requirement_id: Mapped[str] = mapped_column(String(112), primary_key=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.article_id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    object: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[str | None] = mapped_column(String(128), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(128), nullable=True)
    threshold: Mapped[str | None] = mapped_column(String(256), nullable=True)
    exception: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_required: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_articles: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    fact_class: Mapped[str] = mapped_column(String(32), default="FACT", nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="needs_review", nullable=False)
    structured_data: Mapped[dict[str, Any]] = json_column()
    pipeline_run_id: Mapped[str | None] = mapped_column(String(96), nullable=True)

    article: Mapped[Article] = relationship(back_populates="requirements")
    evidence: Mapped[list[Evidence]] = relationship(secondary=requirement_evidence, back_populates="requirements")


class Interpretation(Base):
    __tablename__ = "interpretations"

    interpretation_id: Mapped[str] = mapped_column(String(112), primary_key=True)
    regulation_id: Mapped[str] = mapped_column(ForeignKey("regulations.regulation_id", ondelete="CASCADE"), nullable=False)
    article_id: Mapped[str | None] = mapped_column(ForeignKey("articles.article_id", ondelete="CASCADE"), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    regulatory_meaning: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    conditions: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    exceptions: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    linked_requirements: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), default="Interpretation", nullable=False)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    fact_class: Mapped[str] = mapped_column(String(32), default="INTERPRETATION", nullable=False)
    content_blocks: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, default=list, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(64), default="rule_based", nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    human_lock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    pipeline_run_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    regulation: Mapped[Regulation] = relationship(back_populates="interpretations")
    article: Mapped[Article | None] = relationship(back_populates="interpretations")
    evidence: Mapped[list[Evidence]] = relationship(secondary=interpretation_evidence, back_populates="interpretations")
    content_versions: Mapped[list[ContentVersion]] = relationship(back_populates="interpretation", cascade="all, delete-orphan")


class ContentVersion(Base):
    __tablename__ = "content_versions"

    content_version_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False)
    interpretation_id: Mapped[str] = mapped_column(ForeignKey("interpretations.interpretation_id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot: Mapped[dict[str, Any]] = json_column()
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[Task] = relationship()
    interpretation: Mapped[Interpretation] = relationship(back_populates="content_versions")

    __table_args__ = (UniqueConstraint("interpretation_id", "version_number", name="uq_content_version_number"),)


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.task_id", ondelete="SET NULL"), nullable=True)
    regulation_id: Mapped[str | None] = mapped_column(ForeignKey("regulations.regulation_id", ondelete="SET NULL"), nullable=True)
    article_id: Mapped[str | None] = mapped_column(ForeignKey("articles.article_id", ondelete="SET NULL"), nullable=True)
    source_document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.document_id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    locator: Mapped[dict[str, Any]] = json_column()
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[Task | None] = relationship()
    regulation: Mapped[Regulation | None] = relationship(back_populates="evidence")
    article: Mapped[Article | None] = relationship(back_populates="evidence")
    source_document: Mapped[SourceDocument] = relationship(back_populates="evidence")
    interpretations: Mapped[list[Interpretation]] = relationship(secondary=interpretation_evidence, back_populates="evidence")
    requirements: Mapped[list[Requirement]] = relationship(secondary=requirement_evidence, back_populates="evidence")


class VersionRelation(Base):
    __tablename__ = "version_relations"

    relation_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    regulation_id: Mapped[str] = mapped_column(ForeignKey("regulations.regulation_id", ondelete="CASCADE"), nullable=False)
    from_version_id: Mapped[str] = mapped_column(ForeignKey("regulation_versions.version_id", ondelete="CASCADE"), nullable=False)
    to_version_id: Mapped[str] = mapped_column(ForeignKey("regulation_versions.version_id", ondelete="CASCADE"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    relation_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JsonType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    regulation: Mapped[Regulation] = relationship(back_populates="version_relations", foreign_keys=[regulation_id])
    from_version: Mapped[RegulationVersion] = relationship(back_populates="from_relations", foreign_keys=[from_version_id])
    to_version: Mapped[RegulationVersion] = relationship(back_populates="to_relations", foreign_keys=[to_version_id])


class QCResult(Base):
    __tablename__ = "qc_results"

    qc_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(112), nullable=False)
    check_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    findings: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[Task] = relationship(back_populates="qc_results")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    workflow_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(64), default="REGULATION_INTERPRETATION", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    current_node: Mapped[str | None] = mapped_column(String(32), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requested_from: Mapped[str] = mapped_column(String(32), default="S1", nullable=False)
    params: Mapped[dict[str, Any]] = json_column()
    error_state: Mapped[dict[str, Any]] = json_column()
    celery_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    parent_workflow_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    task: Mapped[Task] = relationship(back_populates="workflow_runs")
    nodes: Mapped[list[WorkflowNode]] = relationship(back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowNode.sequence")


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    node_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.workflow_id", ondelete="CASCADE"), nullable=False)
    node_name: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output: Mapped[dict[str, Any]] = json_column()
    error_state: Mapped[dict[str, Any]] = json_column()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    workflow: Mapped[WorkflowRun] = relationship(back_populates="nodes")

    __table_args__ = (UniqueConstraint("workflow_id", "node_name", name="uq_workflow_node_name"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.task_id", ondelete="SET NULL"), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(112), nullable=False)
    before_state: Mapped[dict[str, Any]] = json_column()
    after_state: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[Task | None] = relationship(back_populates="audit_logs")


class ContentPackage(Base):
    __tablename__ = "content_packages"

    package_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False)
    regulation_id: Mapped[str] = mapped_column(ForeignKey("regulations.regulation_id", ondelete="CASCADE"), nullable=False)
    pipeline_run_id: Mapped[str] = mapped_column(String(96), nullable=False)
    package_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="HUMAN_LOCKED", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_json: Mapped[dict[str, Any]] = json_column()
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    locked_by: Mapped[str] = mapped_column(String(128), nullable=False)
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[Task] = relationship(back_populates="content_packages")
    regulation: Mapped[Regulation] = relationship(back_populates="content_packages")

    __table_args__ = (UniqueConstraint("task_id", "package_version", name="uq_content_package_version"),)
