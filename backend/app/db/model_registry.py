"""Import all models so Alembic and metadata-based tests see every table."""

from backend.app.db.models import (  # noqa: F401
    Article,
    AuditLog,
    ContentPackage,
    ContentVersion,
    Evidence,
    Interpretation,
    Organization,
    OrganizationMember,
    QCResult,
    Regulation,
    RegulationVersion,
    Requirement,
    SourceDocument,
    Task,
    User,
    VersionRelation,
    WorkflowNode,
    WorkflowRun,
)
