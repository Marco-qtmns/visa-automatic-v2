from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from ..classifiers import DocumentClassifier
from ..models.core import utcnow
from ..quality_evaluators import TypeSpecificQualityEvaluator
from ..schemas import core as schemas
from ..storage import StorageProvider
from .classification import DocumentClassificationService
from .core import CoreDataService, DomainNotFound, DomainValidationError
from .documents import DocumentMatchingService, detect_mime_type
from .quality import DocumentQualityService, RequirementCompletenessService


ACCEPTABLE_QUALITY = {
    models.DocumentQualityState.PASSED,
    models.DocumentQualityState.MANUAL_ACCEPTED,
}


class DocumentPipelineService:
    """Source-neutral, idempotent orchestration of the document lifecycle."""

    def __init__(
        self,
        session: Session,
        storage: StorageProvider,
        classifier: DocumentClassifier,
        evaluator: TypeSpecificQualityEvaluator,
    ):
        self.session = session
        self.storage = storage
        self.classifier = classifier
        self.evaluator = evaluator
        self.core = CoreDataService(session)

    def run(
        self,
        document_id: uuid.UUID,
        *,
        idempotency_key: str,
        trigger: str = "explicit",
        retry_of_id: uuid.UUID | None = None,
    ) -> models.DocumentProcessingAttempt:
        document = self.core.get_document(document_id)
        key = idempotency_key.strip()
        if len(key) < 8:
            raise DomainValidationError("idempotency_key must contain at least 8 characters")
        existing = self._by_key(document_id, key)
        if existing is not None:
            return existing
        if retry_of_id is not None:
            previous = self.session.get(models.DocumentProcessingAttempt, retry_of_id)
            if previous is None or previous.document_id != document_id:
                raise DomainValidationError("retry target does not belong to this document")

        attempt = models.DocumentProcessingAttempt(
            document_id=document_id,
            idempotency_key=key,
            retry_of_id=retry_of_id,
            trigger=trigger[:64],
            stage=models.DocumentPipelineStage.RECEIVED.value,
            status=models.DocumentPipelineStatus.RUNNING.value,
            stage_results_json={"received": {"result": "accepted"}},
        )
        self.session.add(attempt)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            duplicate = self._by_key(document_id, key)
            if duplicate is None:
                raise
            return duplicate

        try:
            digest, size = self._basic_validation(document)
            self._stage(attempt, models.DocumentPipelineStage.BASIC_VALIDATION, {
                "result": "passed",
                "document_hash": digest,
                "size_bytes": size,
                "duplicate_document_ids": self._duplicates(document, digest),
            })

            attempt.stage = models.DocumentPipelineStage.QUALITY_ASSESSMENT.value
            self.session.commit()
            quality = DocumentQualityService(self.session, self.storage, self.evaluator).run(document_id)
            self._stage(attempt, models.DocumentPipelineStage.QUALITY_ASSESSMENT, {
                "result": quality.status.value,
                "quality_check_id": str(quality.id),
                "provider": quality.provider,
                "version": quality.evaluator_version,
                "findings": quality.checks_json,
                "issues": quality.issues_json,
            })
            self.session.refresh(document)
            provisional_classification_ready = (
                quality.status == models.QualityCheckStatus.MANUAL_REVIEW
                and {
                    item["check_id"] for item in quality.checks_json
                    if item.get("status") in {"fail", "unknown", "manual_review"}
                } <= {"document_type_assigned"}
            )
            if document.quality_status not in ACCEPTABLE_QUALITY and not provisional_classification_ready:
                return self._needs_review(
                    attempt,
                    problem_type="document_quality",
                    explanation="The document did not pass the quality assessment.",
                    correction="Replace the document or complete a documented manual quality review.",
                    instructions="Please provide a complete, readable scan or photo of the document.",
                )

            if document.classification_status != models.DocumentClassificationState.CONFIRMED:
                attempt.stage = models.DocumentPipelineStage.CLASSIFICATION.value
                self.session.commit()
                classification = DocumentClassificationService(
                    self.session, self.storage, self.classifier
                ).classify(document_id)
                self._stage(attempt, models.DocumentPipelineStage.CLASSIFICATION, {
                    "result": classification.status.value,
                    "classification_id": str(classification.id),
                    "confidence": classification.confidence,
                    "evidence": classification.evidence_json,
                })
                return self._needs_review(
                    attempt,
                    problem_type="classification_review",
                    explanation="Document type or owner requires employee confirmation.",
                    correction="Accept or correct the classification suggestion before matching.",
                    instructions="No customer action is required unless the assigned employee requests another document.",
                )

            self._stage(attempt, models.DocumentPipelineStage.CLASSIFICATION, {
                "result": "confirmed", "source": "authoritative_document_metadata",
            })
            matching = DocumentMatchingService(self.session)
            compatible = matching.compatible_requirements(document_id)
            created_match_ids: list[str] = []
            if len(compatible) == 1:
                requirement = compatible[0]
                existing_match = self.session.scalar(select(models.RequirementDocumentMatch).where(
                    models.RequirementDocumentMatch.requirement_id == requirement.id,
                    models.RequirementDocumentMatch.document_id == document_id,
                ))
                if existing_match is None:
                    match = matching.create_match(
                        requirement.id,
                        document_id,
                        schemas.RequirementDocumentMatchCreate(
                            created_by="system:document-pipeline",
                            note=f"Automatic match from pipeline attempt {attempt.id}",
                        ),
                    )
                    created_match_ids.append(str(match.id))
            self._stage(attempt, models.DocumentPipelineStage.MATCHING, {
                "result": "matched" if created_match_ids else "no_change",
                "compatible_requirement_ids": [str(item.id) for item in compatible],
                "created_match_ids": created_match_ids,
            })
            if len(compatible) > 1:
                return self._needs_review(
                    attempt,
                    problem_type="ambiguous_requirement_match",
                    explanation="More than one requirement can accept this document.",
                    correction="An employee must select the intended requirement.",
                    instructions="No customer action is required.",
                )

            evaluations = RequirementCompletenessService(self.session).evaluate_for_document(
                document_id, trigger="document_pipeline"
            )
            self._stage(attempt, models.DocumentPipelineStage.COMPLETENESS, {
                "result": "evaluated",
                "evaluation_ids": [str(item.id) for item in evaluations],
            })
            attempt.status = models.DocumentPipelineStatus.COMPLETED.value
            attempt.completed_at = utcnow()
            self.session.commit()
            self.session.refresh(attempt)
            return attempt
        except Exception as error:
            self.session.rollback()
            attempt = self.session.get(models.DocumentProcessingAttempt, attempt.id)
            if attempt is None:
                raise
            attempt.status = models.DocumentPipelineStatus.FAILED.value
            attempt.error_code = "pipeline_stage_failed"
            attempt.error_summary = (str(error) or "Document processing failed.")[:500]
            attempt.completed_at = utcnow()
            self.session.commit()
            self._create_issue(
                attempt,
                "processing_failure",
                "Document processing could not be completed.",
                "Retry processing; if it fails again, review the stored document manually.",
                "No customer action is required while the document is retried.",
            )
            self.session.refresh(attempt)
            return attempt

    def retry(
        self, document_id: uuid.UUID, attempt_id: uuid.UUID, *, idempotency_key: str
    ) -> models.DocumentProcessingAttempt:
        return self.run(
            document_id,
            idempotency_key=idempotency_key,
            trigger="retry",
            retry_of_id=attempt_id,
        )

    def list_attempts(self, document_id: uuid.UUID) -> list[models.DocumentProcessingAttempt]:
        self.core.get_document(document_id)
        return list(self.session.scalars(select(models.DocumentProcessingAttempt).where(
            models.DocumentProcessingAttempt.document_id == document_id
        ).order_by(
            models.DocumentProcessingAttempt.created_at.desc(),
            models.DocumentProcessingAttempt.id.desc(),
        )))

    def list_issues(self, document_id: uuid.UUID) -> list[models.DocumentRemediationIssue]:
        self.core.get_document(document_id)
        return list(self.session.scalars(select(models.DocumentRemediationIssue).where(
            models.DocumentRemediationIssue.document_id == document_id
        ).order_by(
            models.DocumentRemediationIssue.created_at.desc(),
            models.DocumentRemediationIssue.id.desc(),
        )))

    def update_issue(
        self, issue_id: uuid.UUID, payload: schemas.DocumentRemediationUpdate
    ) -> models.DocumentRemediationIssue:
        issue = self.session.get(models.DocumentRemediationIssue, issue_id)
        if issue is None:
            raise DomainNotFound("Document remediation issue not found")
        if issue.status != "open":
            raise DomainValidationError("resolved remediation issue cannot be edited")
        issue.notification_draft = payload.notification_draft
        self.session.commit()
        self.session.refresh(issue)
        return issue

    def resolve_issue(
        self, issue_id: uuid.UUID, payload: schemas.DocumentRemediationResolve
    ) -> models.DocumentRemediationIssue:
        issue = self.session.get(models.DocumentRemediationIssue, issue_id)
        if issue is None:
            raise DomainNotFound("Document remediation issue not found")
        issue.status = "resolved"
        issue.resolved_by = payload.resolved_by
        issue.resolved_at = utcnow()
        self.session.commit()
        self.session.refresh(issue)
        return issue

    def _by_key(self, document_id: uuid.UUID, key: str):
        return self.session.scalar(select(models.DocumentProcessingAttempt).where(
            models.DocumentProcessingAttempt.document_id == document_id,
            models.DocumentProcessingAttempt.idempotency_key == key,
        ))

    def _basic_validation(self, document: models.Document) -> tuple[str, int]:
        with self.storage.open(document.storage_path) as source:
            binary = source.read()
        if not binary:
            raise DomainValidationError("stored document is empty")
        if detect_mime_type(binary[:16]) != document.mime_type:
            raise DomainValidationError("stored document format does not match its recorded MIME type")
        return hashlib.sha256(binary).hexdigest(), len(binary)

    def _duplicates(self, document: models.Document, digest: str) -> list[str]:
        duplicate_ids = self.session.scalars(
            select(models.DocumentQualityCheck.document_id).join(models.Document).where(
                models.Document.case_id == document.case_id,
                models.Document.id != document.id,
                models.DocumentQualityCheck.document_hash == digest,
            ).distinct()
        )
        return [str(item) for item in duplicate_ids]

    def _stage(
        self, attempt: models.DocumentProcessingAttempt,
        stage: models.DocumentPipelineStage,
        result: dict[str, object],
    ) -> None:
        attempt.stage = stage.value
        attempt.stage_results_json = {**attempt.stage_results_json, stage.value: result}
        self.session.commit()

    def _needs_review(
        self, attempt, *, problem_type, explanation, correction, instructions
    ) -> models.DocumentProcessingAttempt:
        attempt.status = models.DocumentPipelineStatus.NEEDS_REVIEW.value
        attempt.completed_at = utcnow()
        self.session.commit()
        self._create_issue(attempt, problem_type, explanation, correction, instructions)
        self.session.refresh(attempt)
        return attempt

    def _create_issue(self, attempt, problem_type, explanation, correction, instructions) -> None:
        self.session.add(models.DocumentRemediationIssue(
            document_id=attempt.document_id,
            processing_attempt_id=attempt.id,
            problem_type=problem_type,
            explanation=explanation,
            correction=correction,
            customer_instructions=instructions,
            language="en",
            notification_draft=f"We reviewed your document. {explanation} {instructions}",
        ))
        self.session.commit()
