from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database import Base
from backend.app import models
from backend.app.models import canada as cm


POSTGRES_TEST_URL = os.environ.get("POSTGRES_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="POSTGRES_TEST_DATABASE_URL is required for PostgreSQL baseline tests",
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_REVISION = "0001_consolidated_schema"


def _guard_disposable_database(url: str) -> None:
    parsed = make_url(url)
    database = parsed.database or ""
    if parsed.get_backend_name() != "postgresql":
        raise RuntimeError("PostgreSQL baseline tests require PostgreSQL")
    if not (database.endswith("_test") or "_test_" in database):
        raise RuntimeError("PostgreSQL baseline tests refuse a database not named *_test")


@pytest.fixture(scope="module")
def postgres_engine():
    _guard_disposable_database(POSTGRES_TEST_URL)
    from sqlalchemy import create_engine

    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = POSTGRES_TEST_URL
    config = Config(str(REPOSITORY_ROOT / "backend" / "alembic.ini"))
    try:
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        command.check(config)
        yield engine
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        engine.dispose()


def test_fresh_baseline_matches_metadata(postgres_engine):
    inspector = inspect(postgres_engine)
    tables = set(inspector.get_table_names())
    assert tables - {"alembic_version"} == set(Base.metadata.tables)
    assert len(tables - {"alembic_version"}) == 57
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == EXPECTED_REVISION
        assert connection.scalar(text("SHOW server_version"))


def test_postgresql_catalog_contains_critical_constraints(postgres_engine):
    with postgres_engine.connect() as connection:
        constraint_names = set(connection.scalars(text(
            "SELECT conname FROM pg_constraint "
            "WHERE connamespace = 'public'::regnamespace"
        )))
        index_definitions = {
            row.indexname: row.indexdef
            for row in connection.execute(text(
                "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'"
            ))
        }

    assert {
        "uq_canonical_value_revision",
        "uq_document_pipeline_idempotency",
        "fk_document_processing_retry_same_document",
        "fk_document_remediation_attempt_same_document",
        "uq_requirement_document_match",
        "uq_preparation_run_artifact_type",
        "fk_preparation_artifact_run_case",
        "fk_preparation_approval_run_identity",
        "preparation_approval_target_valid",
    } <= constraint_names
    assert "WHERE ((status)::text = 'running'::text)" in index_definitions["uq_preparation_running_case"]
    assert "WHERE ((role)::text = 'applicant'::text)" in index_definitions["uq_case_one_applicant_role"]


def _expect_integrity(session: Session, value) -> None:
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(value)
            session.flush()


def test_model_operations_and_relational_integrity(postgres_engine):
    now = datetime.now(timezone.utc)
    with Session(postgres_engine, expire_on_commit=False) as session:
        case = models.Case(
            case_number="PG-BASELINE-001", visa_type="TRV", purpose="Synthetic",
            workflow_state=models.WorkflowState.INTAKE,
        )
        second_case = models.Case(
            case_number="PG-BASELINE-002", visa_type="TRV", purpose="Synthetic",
            workflow_state=models.WorkflowState.INTAKE,
        )
        applicant = models.Person(
            case=case, first_name="Synthetic", last_name="Applicant", roles=["applicant"]
        )
        second_person = models.Person(
            case=case, first_name="Synthetic", last_name="Second", roles=[]
        )
        session.add_all([case, second_case, applicant, second_person])
        session.flush()
        session.add(cm.CasePersonRole(
            case_id=case.id, person_id=applicant.id, role="applicant", assigned_by="test"
        ))
        application = cm.CanadaApplication(case_id=case.id, applicant_person_id=applicant.id)
        session.add(application)
        session.flush()
        session.add_all([
            cm.ApplicantResidence(
                application_id=application.id, country_code="BRA", is_current=True
            ),
            cm.TravelDocument(
                application_id=application.id, person_id=applicant.id,
                document_type="passport", number="SYNTHETIC-PASSPORT",
                issuing_country_code="BRA", is_primary=True, sort_order=0,
            ),
            models.Fact(
                case_id=case.id, key="sponsor.exists", value_json=False,
                source_type="manual", source_reference="postgres-test", status="confirmed",
            ),
            models.Fact(
                case_id=case.id, key="host.exists", value_json=False,
                source_type="manual", source_reference="postgres-test", status="confirmed",
            ),
        ])
        import_run = cm.CanadaLegacyImportRun(
            case_id=case.id, source_type="google_verified_csv",
            source_identifier="synthetic.csv", source_hash="a" * 64,
            mapping_version="test-1",
        )
        session.add(import_run)
        session.flush()
        session.add(cm.CanadaImportCandidate(
            import_run_id=import_run.id, domain_section="applicant",
            employee_label="Given names", target_entity_type="person",
            target_entity_id=applicant.id, target_field="first_name",
            source_path="applicant.given_names", source_record_key="scalar",
            source_classification="applicant_direct", source_reference="synthetic:1",
            raw_value_json="Synthetic", proposed_value_json="Synthetic",
            status="same", review_policy="safe_direct_batch",
            conflict_policy="preserve_confirmed",
        ))
        revision = models.CanonicalValueRevision(
            case_id=case.id, field_path="applicant.given_names", entity_type="person",
            entity_id=applicant.id, revision=1, original_value_json=None,
            value_json="Synthetic", source_type="manual", source_reference="postgres-test",
            review_state="confirmed", reviewed_by="test", reviewed_at=now,
        )
        document = models.Document(
            case_id=case.id, person_id=applicant.id, document_type="passport",
            original_filename="synthetic.pdf", storage_path="opaque-synthetic-key",
            mime_type="application/pdf", source_type="upload", metadata_json={},
        )
        requirement = models.Requirement(
            case_id=case.id, document_type="passport", owner_role="applicant",
            owner_person_id=applicant.id, requirement_level="required",
            reason="Synthetic test", is_blocking=True, active=True,
            completeness_policy_json={"mode": "single_document"},
        )
        session.add_all([revision, document, requirement])
        session.flush()
        attempt = models.DocumentProcessingAttempt(
            document_id=document.id, idempotency_key="postgres-baseline-1",
            trigger="test", stage="completeness", status="completed",
            stage_results_json={}, completed_at=now,
        )
        session.add_all([
            attempt,
            models.RequirementDocumentMatch(
                requirement_id=requirement.id, document_id=document.id, created_by="test"
            ),
        ])
        session.flush()
        other_document = models.Document(
            case_id=second_case.id, document_type="other",
            original_filename="other-synthetic.pdf", storage_path="other-opaque-key",
            mime_type="application/pdf", source_type="upload", metadata_json={},
        )
        session.add(other_document)
        session.flush()
        other_attempt = models.DocumentProcessingAttempt(
            document_id=other_document.id, idempotency_key="postgres-baseline-other",
            trigger="test", stage="received", status="completed",
            stage_results_json={}, completed_at=now,
        )
        session.add(other_attempt)
        session.flush()
        session.add(models.DocumentRemediationIssue(
            document_id=document.id, processing_attempt_id=attempt.id,
            problem_type="synthetic", explanation="Synthetic issue",
            correction="Synthetic correction", customer_instructions="Synthetic instructions",
            notification_draft="Synthetic draft",
        ))
        run = models.PreparationRun(
            case_id=case.id, status="succeeded", initiated_by="test",
            payload_schema_version="test", preparation_policy_version="test",
            payload_hash="b" * 64, adapter_version="test", generator_version="test",
            completed_at=now,
        )
        session.add(run)
        session.flush()
        session.add_all([
            models.PreparationArtifact(
                preparation_run_id=run.id, case_id=case.id, artifact_type="imm5257",
                display_filename="IMM5257-DRAFT.pdf", storage_key="artifact-key",
                mime_type="application/pdf", generator="test", generator_version="test",
                template_identifier="test", template_hash="c" * 64, file_hash="d" * 64,
            ),
            models.PreparationApproval(
                case_id=case.id, approval_type="generation", decision="approved",
                payload_hash=run.payload_hash, actor="test",
            ),
            models.PreparationApproval(
                case_id=case.id, preparation_run_id=run.id,
                approval_type="package_review", decision="approved",
                payload_hash=run.payload_hash, actor="test",
            ),
        ])
        user = models.User(
            email="postgres-test@example.invalid", display_name="PostgreSQL Test",
            password_hash="synthetic-not-a-real-hash", role="ADMIN", mfa_enabled=True,
            mfa_secret_encrypted="synthetic",
        )
        session.add(user)
        session.flush()
        session.add(models.AuthSession(
            token_hash="e" * 64, csrf_token_hash="f" * 64, user_id=user.id,
            expires_at=now + timedelta(hours=1),
        ))
        session.commit()

        _expect_integrity(session, models.Case(
            case_number=case.case_number, visa_type="TRV", purpose="Duplicate"
        ))
        _expect_integrity(session, cm.CanadaApplication(case_id=case.id))
        _expect_integrity(session, cm.CasePersonRole(
            case_id=case.id, person_id=second_person.id, role="applicant"
        ))
        _expect_integrity(session, models.CanonicalValueRevision(
            case_id=case.id, field_path=revision.field_path, entity_type="person",
            revision=revision.revision, source_type="manual", source_reference="duplicate",
            review_state="confirmed",
        ))
        _expect_integrity(session, models.DocumentProcessingAttempt(
            document_id=document.id, idempotency_key=attempt.idempotency_key,
            trigger="test", stage="received", status="running", stage_results_json={},
        ))
        _expect_integrity(session, models.DocumentProcessingAttempt(
            document_id=other_document.id, retry_of_id=attempt.id,
            idempotency_key="cross-document-retry", trigger="test",
            stage="received", status="running", stage_results_json={},
        ))
        _expect_integrity(session, models.DocumentProcessingAttempt(
            document_id=document.id, idempotency_key="invalid-stage", trigger="test",
            stage="not-a-stage", status="running", stage_results_json={},
        ))
        _expect_integrity(session, models.DocumentRemediationIssue(
            document_id=other_document.id, processing_attempt_id=attempt.id,
            problem_type="cross-document", explanation="Synthetic issue",
            correction="Synthetic correction", customer_instructions="Synthetic",
            notification_draft="Synthetic",
        ))
        _expect_integrity(session, models.DocumentRemediationIssue(
            document_id=document.id, processing_attempt_id=attempt.id,
            problem_type="invalid-resolution", explanation="Synthetic issue",
            correction="Synthetic correction", customer_instructions="Synthetic",
            notification_draft="Synthetic", status="resolved",
        ))
        _expect_integrity(session, models.RequirementDocumentMatch(
            requirement_id=requirement.id, document_id=document.id
        ))
        first_running = models.PreparationRun(
            case_id=case.id, status="running", initiated_by="test",
            payload_schema_version="test", preparation_policy_version="test",
            payload_hash="1" * 64, adapter_version="test", generator_version="test",
        )
        session.add(first_running)
        session.commit()
        _expect_integrity(session, models.PreparationRun(
            case_id=case.id, status="running", initiated_by="test",
            payload_schema_version="test", preparation_policy_version="test",
            payload_hash="2" * 64, adapter_version="test", generator_version="test",
        ))
        _expect_integrity(session, models.PreparationArtifact(
            preparation_run_id=run.id, case_id=case.id, artifact_type="imm5257",
            display_filename="duplicate.pdf", storage_key="duplicate", mime_type="application/pdf",
            generator="test", generator_version="test", template_identifier="test",
            template_hash="3" * 64, file_hash="4" * 64,
        ))
        _expect_integrity(session, models.PreparationArtifact(
            preparation_run_id=run.id, case_id=second_case.id, artifact_type="imm5707",
            display_filename="wrong-case.pdf", storage_key="wrong-case",
            mime_type="application/pdf", generator="test", generator_version="test",
            template_identifier="test", template_hash="3" * 64, file_hash="4" * 64,
        ))
        _expect_integrity(session, models.PreparationApproval(
            case_id=case.id, preparation_run_id=run.id,
            approval_type="package_review", decision="approved",
            payload_hash="wrong-hash", actor="test",
        ))
        _expect_integrity(session, models.PreparationApproval(
            case_id=second_case.id, preparation_run_id=run.id,
            approval_type="package_review", decision="approved",
            payload_hash=run.payload_hash, actor="test",
        ))
        _expect_integrity(session, models.PreparationApproval(
            case_id=case.id, preparation_run_id=run.id,
            approval_type="generation", decision="approved",
            payload_hash=run.payload_hash, actor="test",
        ))

        session.delete(other_document)
        session.commit()
        assert session.get(models.DocumentProcessingAttempt, other_attempt.id) is None

    def rejected(statement: str, parameters: dict) -> None:
        with postgres_engine.connect() as connection:
            transaction = connection.begin()
            try:
                with pytest.raises(IntegrityError):
                    connection.execute(text(statement), parameters)
            finally:
                transaction.rollback()

    rejected(
        "INSERT INTO documents "
        "(id, case_id, original_filename, storage_path, mime_type, source_type, "
        "classification_status, quality_status, metadata_json, created_at, updated_at) "
        "VALUES (:id, :case_id, 'x.pdf', 'x', 'application/pdf', 'upload', "
        "'unclassified', 'not_checked', '{}'::jsonb, now(), now())",
        {"id": uuid.uuid4(), "case_id": uuid.uuid4()},
    )
    rejected(
        "UPDATE document_processing_attempts SET status = 'invalid' WHERE id = :id",
        {"id": attempt.id},
    )

    with Session(postgres_engine) as session:
        assert session.scalar(select(models.Case).where(
            models.Case.case_number == "PG-BASELINE-001"
        )) is not None
