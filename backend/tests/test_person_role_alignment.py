from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from backend.app import models
from backend.app.database import get_session
from backend.app.main import app
from backend.app.models import canada as cm
from backend.app.schemas.core import PersonCreate, PersonRead
from backend.app.services.core import CoreDataService


def test_person_api_and_canonical_operational_role_vocabularies_are_identical():
    expected = {role.value for role in cm.OperationalRole}
    assert expected == {"applicant", "representative", "sponsor", "host", "other"}
    for role in expected:
        assert PersonCreate(first_name="Valid", last_name="Person", roles=[role]).roles
    for relationship in ("spouse", "former_spouse", "parent", "child", "family_member"):
        with pytest.raises(ValidationError):
            PersonCreate(first_name="Invalid", last_name="Role", roles=[relationship])


def test_core_person_writes_normalized_roles_and_projection_together(session):
    case = models.Case(case_number="ROLE-SYNC", visa_type="canada_trv", purpose="Test")
    session.add(case)
    session.commit()
    person = CoreDataService(session).create_person(
        case.id, PersonCreate(first_name="Dual", last_name="Role", roles=["sponsor", "host"])
    )
    assert person.roles == ["sponsor", "host"]
    assert set(session.scalars(select(cm.CasePersonRole.role).where(
        cm.CasePersonRole.person_id == person.id
    ))) == {"sponsor", "host"}
    assert PersonRead.model_validate(person).roles


def test_people_endpoint_normalizes_legacy_family_role_without_500(session):
    case = models.Case(case_number="LEGACY-API", visa_type="canada_trv", purpose="Test")
    session.add(case)
    session.flush()
    person = models.Person(
        case_id=case.id, first_name="Legacy", last_name="Relative", roles=["family_member"]
    )
    session.add(person)
    session.commit()

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    try:
        response = TestClient(app).get(f"/cases/{case.id}/persons")
        assert response.status_code == 200
        assert response.json()[0]["roles"] == ["other"]
    finally:
        app.dependency_overrides.pop(get_session, None)
