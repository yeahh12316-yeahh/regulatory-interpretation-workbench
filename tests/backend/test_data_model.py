from datetime import date

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from backend.app.db import model_registry  # noqa: F401
from backend.app.db.base import Base
from backend.app.db.models import (
    Article,
    AuditLog,
    Evidence,
    Interpretation,
    Regulation,
    RegulationVersion,
    Requirement,
    SourceDocument,
    Task,
)


def test_schema_contains_step_seven_domain_objects():
    expected = {
        "tasks",
        "source_documents",
        "regulations",
        "regulation_versions",
        "articles",
        "requirements",
        "interpretations",
        "evidence",
        "version_relations",
        "qc_results",
        "audit_logs",
        "interpretation_evidence",
        "requirement_evidence",
    }
    assert expected <= set(Base.metadata.tables)


def test_evidence_chain_and_audit_log_persist_in_sqlite():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        task = Task(task_id="TASK_001", task_name="呆账核销管理办法解读", created_by="tester")
        source = SourceDocument(
            document_id="DOC_001",
            task=task,
            file_name="财政部关于印发《金融企业呆账核销管理办法（2017年版）》的通知.pdf",
            source_type="official_pdf",
            storage_key="sources/2017-mof-bad-debt.pdf",
            sha256="8bd8290816f7ba9dbba81def4e725fbfccdea984a0f616f2bb00a98a6b8c2da8",
            page_count=4,
        )
        regulation = Regulation(
            regulation_id="FIN_MOF_2017_90",
            title="金融企业呆账核销管理办法（2017年版）",
            document_no="财金〔2017〕90号",
            issuer=["财政部"],
        )
        version = RegulationVersion(
            version_id="FIN_MOF_2017_90_V1",
            regulation=regulation,
            version_label="2017年版",
            effective_date=date(2017, 10, 1),
            source_document=source,
            source_sha256=source.sha256,
        )
        article = Article(
            article_id="FIN_MOF_2017_90_ART_001",
            version=version,
            article_no="第一条",
            article_order=1,
            original_text="为加强金融企业呆账核销管理，制定本办法。",
            source_page=1,
        )
        requirement = Requirement(
            requirement_id="FIN_MOF_2017_90_ART_001_REQ_001",
            article=article,
            rule_type="PRIN",
            source_text=article.original_text,
            subject="金融企业",
        )
        interpretation = Interpretation(
            interpretation_id="FIN_MOF_2017_90_ART_001_INT_001",
            regulation=regulation,
            article=article,
            summary="本条明确制定办法的目的。",
            review_status="pending",
        )
        evidence = Evidence(
            evidence_id="EVID_001",
            task=task,
            regulation=regulation,
            article=article,
            source_document=source,
            source_type="official_pdf",
            locator={"page": 1, "article_no": "第一条"},
            source_text=article.original_text,
            verification_status="verified",
        )
        interpretation.evidence.append(evidence)
        requirement.evidence.append(evidence)
        audit = AuditLog(
            audit_id="AUDIT_001",
            task=task,
            actor_id="tester",
            action="create",
            entity_type="interpretation",
            entity_id=interpretation.interpretation_id,
            after_state={"review_status": "pending"},
        )
        session.add_all([task, source, regulation, version, article, requirement, interpretation, evidence, audit])
        session.commit()

        saved = session.get(Interpretation, interpretation.interpretation_id)
        assert saved is not None
        assert saved.evidence[0].locator["page"] == 1
        assert saved.article.original_text == article.original_text
        assert session.get(AuditLog, "AUDIT_001").entity_id == interpretation.interpretation_id
        assert inspect(engine).has_table("version_relations")
