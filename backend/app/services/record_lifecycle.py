from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..models.auth import User
from ..authorization import Permission, enforce_permission
from ..models.intake import IntakeProcessingAttempt, IntakeSubmission
from .audit import record_audit
from .core import DomainNotFound, DomainValidationError


class RecordLifecycleService:
    """Retention-safe lifecycle operations for cases and intake submissions."""

    def __init__(self, session: Session):
        self.session = session

    def archive_case(self, case_id: uuid.UUID, actor: User) -> models.Case:
        enforce_permission(actor, Permission.CASE_ARCHIVE)
        case = self._case(case_id)
        if case.record_status == "ARCHIVED":
            return case
        if case.record_status == "DELETED":
            raise DomainValidationError("deleted applications cannot be archived")
        now = datetime.now(timezone.utc)
        case.record_status = "ARCHIVED"
        case.archived_at = now
        case.archived_by = actor.email
        self._audit(actor, "CASE_ARCHIVED", "CASE", case.id, case.id)
        self.session.commit()
        self.session.refresh(case)
        return case

    def restore_case(self, case_id: uuid.UUID, actor: User) -> models.Case:
        enforce_permission(actor, Permission.CASE_ARCHIVE)
        case = self._case(case_id)
        if case.record_status == "ACTIVE":
            return case
        if case.record_status == "DELETED":
            raise DomainValidationError("deleted applications cannot be restored from the archive")
        case.record_status = "ACTIVE"
        case.archived_at = None
        case.archived_by = None
        self._audit(actor, "CASE_RESTORED", "CASE", case.id, case.id)
        self.session.commit()
        self.session.refresh(case)
        return case

    def delete_case(self, case_id: uuid.UUID, actor: User) -> models.Case:
        enforce_permission(actor, Permission.CASE_DELETE)
        case = self._case(case_id)
        if case.record_status == "DELETED":
            return case
        dependencies = self._case_dependencies(case.id)
        now = datetime.now(timezone.utc)
        case.record_status = "DELETED"
        case.deleted_at = now
        case.deleted_by = actor.email
        self._audit(
            actor, "CASE_RETENTION_DELETE", "CASE", case.id, case.id,
            metadata={"mode": "soft_delete", "retained_dependencies": dependencies},
        )
        self.session.commit()
        self.session.refresh(case)
        return case

    def archive_intake(self, submission_id: uuid.UUID, actor: User) -> IntakeSubmission:
        enforce_permission(actor, Permission.INTAKE_ARCHIVE)
        item = self._intake(submission_id)
        if item.record_status == "ARCHIVED":
            return item
        if item.record_status == "DELETED":
            raise DomainValidationError("deleted intake submissions cannot be archived")
        item.record_status = "ARCHIVED"
        item.archived_at = datetime.now(timezone.utc)
        item.archived_by = actor.email
        self._audit(actor, "INTAKE_ARCHIVED", "INTAKE_SUBMISSION", item.id, item.case_id)
        self.session.commit()
        self.session.refresh(item)
        return item

    def restore_intake(self, submission_id: uuid.UUID, actor: User) -> IntakeSubmission:
        enforce_permission(actor, Permission.INTAKE_ARCHIVE)
        item = self._intake(submission_id)
        if item.record_status == "ACTIVE":
            return item
        if item.record_status == "DELETED":
            raise DomainValidationError("deleted intake submissions cannot be restored from the archive")
        item.record_status = "ACTIVE"
        item.archived_at = None
        item.archived_by = None
        self._audit(actor, "INTAKE_RESTORED", "INTAKE_SUBMISSION", item.id, item.case_id)
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete_intake(self, submission_id: uuid.UUID, actor: User) -> IntakeSubmission:
        enforce_permission(actor, Permission.INTAKE_DELETE)
        item = self._intake(submission_id)
        if item.record_status == "DELETED":
            return item
        attempt_count = int(self.session.scalar(select(func.count(IntakeProcessingAttempt.id)).where(
            IntakeProcessingAttempt.submission_id == item.id
        )) or 0)
        item.record_status = "DELETED"
        item.deleted_at = datetime.now(timezone.utc)
        item.deleted_by = actor.email
        self._audit(
            actor, "INTAKE_RETENTION_DELETE", "INTAKE_SUBMISSION", item.id, item.case_id,
            metadata={
                "mode": "soft_delete", "retained_attempts": attempt_count,
                "raw_source_retained": True, "linked_case_retained": item.case_id is not None,
            },
        )
        self.session.commit()
        self.session.refresh(item)
        return item

    def _case(self, case_id: uuid.UUID) -> models.Case:
        case = self.session.get(models.Case, case_id)
        if case is None:
            raise DomainNotFound("Case not found")
        return case

    def _intake(self, submission_id: uuid.UUID) -> IntakeSubmission:
        item = self.session.get(IntakeSubmission, submission_id)
        if item is None:
            raise DomainNotFound("Intake submission not found")
        return item

    def _case_dependencies(self, case_id: uuid.UUID) -> dict[str, int]:
        return {
            "persons": int(self.session.scalar(select(func.count(models.Person.id)).where(models.Person.case_id == case_id)) or 0),
            "documents": int(self.session.scalar(select(func.count(models.Document.id)).where(models.Document.case_id == case_id)) or 0),
            "audit_events": int(self.session.scalar(select(func.count(models.ApplicationAuditEvent.id)).where(models.ApplicationAuditEvent.case_id == case_id)) or 0),
            "intake_submissions": int(self.session.scalar(select(func.count(IntakeSubmission.id)).where(IntakeSubmission.case_id == case_id)) or 0),
        }

    def _audit(
        self, actor: User, action: str, entity_type: str,
        entity_id: uuid.UUID, case_id: uuid.UUID | None,
        metadata: dict | None = None,
    ) -> None:
        record_audit(
            self.session, actor=actor, action=action,
            target_entity_type=entity_type, target_entity_id=entity_id,
            case_id=case_id, metadata=metadata,
        )
