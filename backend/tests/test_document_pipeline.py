from __future__ import annotations

import io

import pymupdf

from backend.app import models
from backend.app.classifiers import ClassificationEvidenceItem, ClassifierResult
from backend.app.quality_evaluators import QualityCheckFinding, TypeSpecificQualityResult
from backend.app.schemas import core as schemas
from backend.app.services import (
    CoreDataService,
    DocumentClassificationService,
    DocumentPipelineService,
    DocumentUploadService,
    DynamicCaseService,
)
from backend.app.storage import LocalStorageProvider


def pdf_bytes(text: str = "Synthetic Bank Statement Account holder: Carlos Silva") -> bytes:
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), text)
    value = pdf.tobytes()
    pdf.close()
    return value


class PipelineClassifier:
    name = "pipeline_test"
    model_version = "1"

    def classify(self, _content):
        return ClassifierResult(
            document_type="bank_statements",
            owner_name="Carlos Silva",
            confidence=0.95,
            evidence=[ClassificationEvidenceItem("classification", "Synthetic bank statement")],
        )


class PassingEvaluator:
    name = "pipeline_test"
    version = "1"

    def evaluate(self, _content, checks):
        return TypeSpecificQualityResult(
            checks=[QualityCheckFinding(
                check_id=item.check_id,
                status="pass",
                evidence="Synthetic pass",
                issue=None,
                evaluator=self.name,
            ) for item in checks],
            extracted_metadata={},
        )


def pipeline_fixture(session, tmp_path):
    core = CoreDataService(session)
    case = core.create_case(schemas.CaseCreate(
        case_number="PIPELINE-1", visa_type="TRV", purpose="Synthetic"
    ))
    person = core.create_person(case.id, schemas.PersonCreate(
        first_name="Carlos", last_name="Silva", roles=["sponsor"]
    ))
    storage = LocalStorageProvider(tmp_path / "pipeline-storage")
    document = DocumentUploadService(session, storage).upload(
        case.id,
        io.BytesIO(pdf_bytes()),
        original_filename="statement.pdf",
        declared_mime_type="application/pdf",
    )
    service = DocumentPipelineService(
        session, storage, PipelineClassifier(), PassingEvaluator()
    )
    return case, person, document, storage, service


def test_pipeline_is_idempotent_and_creates_editable_remediation(session, tmp_path):
    _case, _person, document, _storage, service = pipeline_fixture(session, tmp_path)

    first = service.run(document.id, idempotency_key="request-0001")
    duplicate = service.run(document.id, idempotency_key="request-0001")

    assert duplicate.id == first.id
    assert first.status == "needs_review"
    assert first.stage == "classification"
    assert len(service.list_attempts(document.id)) == 1
    issues = service.list_issues(document.id)
    assert issues[0].problem_type == "classification_review"
    assert "never" not in issues[0].notification_draft.casefold()
    dynamic = DynamicCaseService(session).status(document.case_id)
    assert any(item["source_id"] == issues[0].id for item in dynamic["issues"])

    updated = service.update_issue(issues[0].id, schemas.DocumentRemediationUpdate(
        notification_draft="Employee-edited draft; do not send automatically."
    ))
    assert updated.notification_draft.startswith("Employee-edited")
    resolved = service.resolve_issue(issues[0].id, schemas.DocumentRemediationResolve(
        resolved_by="employee"
    ))
    assert resolved.status == "resolved"


def test_confirmed_good_document_matches_and_completes_requirement(session, tmp_path):
    case, person, document, storage, service = pipeline_fixture(session, tmp_path)
    classification_service = DocumentClassificationService(
        session, storage, PipelineClassifier()
    )
    suggestion = classification_service.classify(document.id)
    classification_service.accept(document.id, suggestion.id, "employee")
    requirement = models.Requirement(
        case_id=case.id,
        document_type="bank_statements",
        owner_role="sponsor",
        owner_person_id=person.id,
        requirement_level="required",
        reason="Funding evidence",
        is_blocking=True,
        active=True,
        fulfillment_status=models.RequirementFulfillmentStatus.PENDING,
    )
    session.add(requirement)
    session.commit()

    attempt = service.run(document.id, idempotency_key="request-0002")
    session.refresh(requirement)

    assert attempt.status == "completed"
    assert attempt.stage == "completeness"
    assert requirement.fulfillment_status == models.RequirementFulfillmentStatus.FULFILLED
    matches = session.query(models.RequirementDocumentMatch).filter_by(
        requirement_id=requirement.id, document_id=document.id
    ).all()
    assert len(matches) == 1


def test_retry_is_linked_and_isolated_to_one_document(session, tmp_path):
    _case, _person, document, _storage, service = pipeline_fixture(session, tmp_path)
    first = service.run(document.id, idempotency_key="request-0003")
    retry = service.retry(document.id, first.id, idempotency_key="request-0004")

    assert retry.id != first.id
    assert retry.retry_of_id == first.id
    assert len(service.list_attempts(document.id)) == 2
