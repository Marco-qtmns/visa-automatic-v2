from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app import models
from backend.app.models.audit import ApplicationAuditEvent
from backend.app.models.intake import IntakeSubmission
from backend.app.services.core import CoreDataService
from backend.app.services.intake import IntakeService
from backend.app.services.record_lifecycle import RecordLifecycleService
from backend.app.storage import LocalStorageProvider


def actor(role: str):
    return SimpleNamespace(
        id=None, email=f"{role.casefold()}@example.invalid", display_name=role,
        role=role, is_active=True,
    )


def test_case_archive_restore_and_admin_retention_delete(session):
    case = models.Case(
        case_number="LIFECYCLE-CASE-1", visa_type="TRV", purpose="Synthetic",
        workflow_state=models.WorkflowState.INTAKE,
    )
    session.add(case); session.commit()
    lifecycle = RecordLifecycleService(session)

    lifecycle.archive_case(case.id, actor("CASE_WORKER"))
    assert CoreDataService(session).list_cases(view="active") == []
    assert [item.id for item in CoreDataService(session).list_cases(view="archived")] == [case.id]

    lifecycle.restore_case(case.id, actor("CASE_WORKER"))
    assert case.record_status == "ACTIVE" and case.archived_at is None

    with pytest.raises(HTTPException) as denied:
        lifecycle.delete_case(case.id, actor("CASE_WORKER"))
    assert denied.value.status_code == 403

    lifecycle.delete_case(case.id, actor("ADMIN"))
    assert case.record_status == "DELETED"
    assert CoreDataService(session).list_cases(view="active") == []
    actions = set(session.scalars(select(ApplicationAuditEvent.action)))
    assert {"CASE_ARCHIVED", "CASE_RESTORED", "CASE_RETENTION_DELETE"} <= actions


def test_intake_archive_restore_and_admin_retention_delete(session, tmp_path):
    item = IntakeSubmission(
        source_type="GOOGLE_FORMS_CSV", source_filename="synthetic.csv",
        source_hash="a" * 64, source_size_bytes=10,
        raw_source_reference="retained/synthetic.csv", mapping_version="test-1",
        processing_status="NEEDS_REVIEW",
    )
    session.add(item); session.commit()
    lifecycle = RecordLifecycleService(session)
    intake = IntakeService(session, LocalStorageProvider(tmp_path / "intake"))

    lifecycle.archive_intake(item.id, actor("CASE_WORKER"))
    assert intake.list(view="active") == []
    assert [value.id for value in intake.list(view="archived")] == [item.id]

    lifecycle.restore_intake(item.id, actor("CASE_WORKER"))
    assert item.record_status == "ACTIVE" and item.archived_at is None

    with pytest.raises(HTTPException) as denied:
        lifecycle.delete_intake(item.id, actor("CASE_WORKER"))
    assert denied.value.status_code == 403

    lifecycle.delete_intake(item.id, actor("ADMIN"))
    assert item.record_status == "DELETED"
    assert intake.list(view="active") == []
    assert item.raw_source_reference == "retained/synthetic.csv"
    actions = set(session.scalars(select(ApplicationAuditEvent.action)))
    assert {"INTAKE_ARCHIVED", "INTAKE_RESTORED", "INTAKE_RETENTION_DELETE"} <= actions
