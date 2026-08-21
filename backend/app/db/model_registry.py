"""Import all models so Alembic and metadata-based tests see every table."""

from backend.app.db.models import (  # noqa: F401
    Article,
    AuditLog,
    Evidence,
    Interpretation,
    QCResult,
    Regulation,
    RegulationVersion,
    Requirement,
    SourceDocument,
    Task,
    VersionRelation,
)
