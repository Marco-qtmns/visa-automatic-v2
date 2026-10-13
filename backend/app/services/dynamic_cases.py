from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import models
from ..models import canada as cm
from ..schemas import core as schemas
from .canada_preparation import CanadaPreparationReadinessService
from .core import DomainNotFound, DomainValidationError
from .country_normalization import normalize_country
from .person_roles import add_authoritative_role
from .requirements import RequirementEngine


FACT_FIELDS = frozenset({
    "sponsor.exists", "host.exists", "trip.payer", "destination.country_code",
    "commercial.instructions", "special.circumstances", "additional.notes",
})
BOOLEAN_FIELDS = frozenset({"sponsor.exists", "host.exists"})
TEXT_FIELDS = frozenset({
    "case.visa_type", "applicant.given_names", "applicant.family_name",
    "applicant.biography.other_names", "applicant.biography.birth_city",
    "applicant.biography.birth_state_province",
    "contact.email", "contact.phone", "trip.purpose", "destination.country_code",
    "commercial.instructions", "special.circumstances", "additional.notes",
    "applicant.passport.number", "applicant.residential_address.street_number",
    "applicant.residential_address.street_name", "applicant.residential_address.city",
    "applicant.residential_address.state_province", "applicant.residential_address.postal_code",
    "trip.imm5257_purpose_code", "trip.available_funds_currency", "trip.funds_source_reference",
})
PERSON_REFERENCE_FIELDS = frozenset({"sponsor.person_id", "host.person_id"})
BIOGRAPHY_FIELDS = frozenset({
    "applicant.biography.date_of_birth", "applicant.biography.other_names",
    "applicant.biography.sex", "applicant.biography.birth_city",
    "applicant.biography.birth_state_province", "applicant.biography.birth_country_code",
    "applicant.biography.marital_status",
})
SEX_VALUES = frozenset({"female", "male", "another_gender", "unknown"})
MARITAL_STATUS_VALUES = frozenset({
    "single", "married", "common_law", "widowed", "divorced",
    "separated", "annulled_marriage", "unknown",
})
DATE_FIELDS = frozenset({
    "applicant.passport.issue_date", "applicant.passport.expiry_date",
    "application.official_application_date", "trip.arrival_date", "trip.departure_date",
})
COUNTRY_FIELDS = frozenset({
    "applicant.current_residence.country_code", "applicant.passport.issuing_country_code",
    "applicant.residential_address.country_code",
})


class CanonicalDecisionService:
    """Writes manual/provider decisions to typed authority plus an immutable revision ledger."""

    def __init__(self, session: Session):
        self.session = session

    def apply(self, case_id: uuid.UUID, payload: schemas.CanonicalDecisionBatch):
        case = self.session.get(models.Case, case_id)
        if case is None:
            raise DomainNotFound("Case not found")
        decisions = {item.field_path: item.value_json for item in payload.decisions}
        if len(decisions) != len(payload.decisions):
            raise DomainValidationError("each canonical field may appear only once per decision batch")
        self._validate(decisions)
        for item in payload.decisions:
            current_revision = self.session.scalar(select(func.max(models.CanonicalValueRevision.revision)).where(
                models.CanonicalValueRevision.case_id == case_id,
                models.CanonicalValueRevision.field_path == item.field_path,
            )) or 0
            if item.expected_revision != current_revision:
                raise DomainValidationError(
                    f"stale canonical value for {item.field_path}; reload the Case before saving"
                )
        applicant = self._applicant(case_id)
        if applicant is not None and self.session.scalar(select(cm.CasePersonRole.id).where(
            cm.CasePersonRole.case_id == case_id,
            cm.CasePersonRole.person_id == applicant.id,
            cm.CasePersonRole.role == cm.OperationalRole.APPLICANT,
        )) is None:
            add_authoritative_role(
                self.session, applicant, cm.OperationalRole.APPLICANT,
                assigned_by=payload.reviewed_by,
            )
        if applicant is None and any(
            path.startswith(("applicant.", "contact.")) or path == "trip.purpose"
            for path in decisions
        ):
            given = decisions.get("applicant.given_names")
            family = decisions.get("applicant.family_name")
            if not isinstance(given, str) or not given.strip() or not isinstance(family, str) or not family.strip():
                raise DomainValidationError(
                    "given and family names are required when creating the canonical applicant"
                )
            applicant = models.Person(
                case_id=case_id, first_name=given.strip(), last_name=family.strip(), roles=["applicant"]
            )
            self.session.add(applicant)
            self.session.flush()
            add_authoritative_role(
                self.session, applicant, cm.OperationalRole.APPLICANT,
                assigned_by=payload.reviewed_by,
            )
        app = self._application(case_id, applicant)
        now = datetime.now(timezone.utc)
        revisions = []
        try:
            for field_path, value in decisions.items():
                old_value, entity_type, entity_id = self._write(
                    case, app, applicant, field_path, value, payload
                )
                item = self.append_revision(
                    case_id=case_id, field_path=field_path, entity_type=entity_type,
                    entity_id=entity_id, original_value=old_value, value=value,
                    source_type=payload.source_type,
                    source_reference=payload.source_reference,
                    source_timestamp=payload.source_timestamp,
                    source_version=payload.source_version,
                    review_state="needs_review" if value is None else (
                        "confirmed" if old_value in (None, "") or old_value == value else "corrected"
                    ), reviewed_by=payload.reviewed_by, reviewed_at=now,
                )
                revisions.append(item)
            self.session.flush()
            RequirementEngine(self.session).evaluate(case_id)
        except Exception:
            self.session.rollback()
            raise
        for item in revisions:
            self.session.refresh(item)
        return revisions

    def append_revision(
        self, *, case_id, field_path, entity_type, entity_id, original_value, value,
        source_type, source_reference, review_state, reviewed_by,
        source_timestamp=None, source_version=None, reviewed_at=None,
    ):
        revision = (self.session.scalar(select(func.max(models.CanonicalValueRevision.revision)).where(
            models.CanonicalValueRevision.case_id == case_id,
            models.CanonicalValueRevision.field_path == field_path,
        )) or 0) + 1
        item = models.CanonicalValueRevision(
            case_id=case_id, field_path=field_path, entity_type=entity_type,
            entity_id=entity_id, revision=revision,
            original_value_json=original_value, value_json=value,
            source_type=source_type, source_reference=source_reference,
            source_timestamp=source_timestamp, source_version=source_version,
            review_state=review_state, reviewed_by=reviewed_by,
            reviewed_at=reviewed_at or datetime.now(timezone.utc),
        )
        self.session.add(item)
        return item

    def _validate(self, decisions: dict[str, Any]) -> None:
        for path, value in decisions.items():
            if path in BOOLEAN_FIELDS and value is not None and not isinstance(value, bool):
                raise DomainValidationError(f"{path} must be yes, no, or unknown")
            if path == "trip.payer" and value is not None and value not in {"applicant", "sponsor", "other", "mixed"}:
                raise DomainValidationError("trip.payer must be applicant, sponsor, other, mixed, or unknown")
            if path in TEXT_FIELDS and value is not None and (not isinstance(value, str) or not value.strip()):
                raise DomainValidationError(f"{path} must be non-empty text or unknown")
            if path == "application.mailing_same_as_residential" and value is not None and not isinstance(value, bool):
                raise DomainValidationError("mailing-address choice must be yes, no, or unresolved")
            if path in DATE_FIELDS and value is not None:
                try:
                    date.fromisoformat(str(value))
                except ValueError:
                    raise DomainValidationError(f"{path} must use YYYY-MM-DD") from None
            if path == "applicant.biography.date_of_birth" and value is not None:
                try:
                    parsed = date.fromisoformat(str(value))
                except ValueError:
                    raise DomainValidationError("date of birth must use YYYY-MM-DD") from None
                if parsed > date.today():
                    raise DomainValidationError("date of birth cannot be in the future")
            if path == "applicant.biography.sex" and value is not None and value not in SEX_VALUES:
                raise DomainValidationError("sex must be female, male, another gender, unknown, or unresolved")
            if path == "applicant.biography.marital_status" and value is not None and value not in MARITAL_STATUS_VALUES:
                raise DomainValidationError("marital status is not supported by the official application")
            if path in {"applicant.biography.birth_country_code", "applicant.citizenship.primary"} and value is not None:
                if normalize_country(value).code is None:
                    raise DomainValidationError(f"{path} must be a recognized ISO country")
            if path in COUNTRY_FIELDS and value is not None and normalize_country(value).code is None:
                raise DomainValidationError(f"{path} must be a recognized ISO country")
            if path == "trip.available_funds_amount" and value is not None:
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                    raise DomainValidationError("available funds must be a non-negative number")
            if path == "destination.country_code" and value is not None and len(value.strip()) not in {2, 3}:
                raise DomainValidationError("destination country must be an ISO alpha-2 or alpha-3 code")
            if path in PERSON_REFERENCE_FIELDS and value is not None:
                try:
                    uuid.UUID(str(value))
                except (TypeError, ValueError):
                    raise DomainValidationError(f"{path} must identify a person in this case") from None

    def _applicant(self, case_id):
        role = self.session.scalar(select(cm.CasePersonRole).where(
            cm.CasePersonRole.case_id == case_id,
            cm.CasePersonRole.role == cm.OperationalRole.APPLICANT,
        ))
        if role:
            return self.session.get(models.Person, role.person_id)
        app = self.session.scalar(select(cm.CanadaApplication).where(cm.CanadaApplication.case_id == case_id))
        return self.session.get(models.Person, app.applicant_person_id) if app and app.applicant_person_id else None

    def _application(self, case_id, applicant):
        app = self.session.scalar(select(cm.CanadaApplication).where(cm.CanadaApplication.case_id == case_id))
        if app is None and applicant is not None:
            app = cm.CanadaApplication(case_id=case_id, applicant_person_id=applicant.id)
            self.session.add(app)
            self.session.flush()
        elif app is not None and app.applicant_person_id is None and applicant is not None:
            app.applicant_person_id = applicant.id
        return app

    def _write(self, case, app, applicant, path, value, payload):
        if path == "case.visa_type":
            old = case.visa_type
            case.visa_type = value.strip()
            return old, "case", case.id
        if path in {"applicant.given_names", "applicant.family_name"}:
            if applicant is None:
                raise DomainValidationError("canonical applicant is unavailable")
            attr = "first_name" if path.endswith("given_names") else "last_name"
            old = getattr(applicant, attr)
            setattr(applicant, attr, value.strip())
            return old, "person", applicant.id
        if path in BIOGRAPHY_FIELDS:
            if applicant is None:
                raise DomainValidationError("canonical applicant is unavailable")
            biography = self.session.get(cm.PersonBiography, applicant.id)
            if biography is None:
                biography = cm.PersonBiography(person_id=applicant.id)
                self.session.add(biography)
            attr = path.rsplit(".", 1)[1]
            old = getattr(biography, attr)
            if attr == "date_of_birth":
                normalized = date.fromisoformat(str(value)) if value is not None else None
            elif attr == "birth_country_code":
                normalized = normalize_country(value).code if value is not None else None
            else:
                normalized = value.strip() if isinstance(value, str) else value
            setattr(biography, attr, normalized)
            self.session.flush()
            return old.isoformat() if isinstance(old, date) else old, "person_biography", applicant.id
        if path == "applicant.citizenship.primary":
            if applicant is None:
                raise DomainValidationError("canonical applicant is unavailable")
            code = normalize_country(value).code if value is not None else None
            current = self.session.scalar(select(cm.PersonCitizenship).where(
                cm.PersonCitizenship.person_id == applicant.id,
                cm.PersonCitizenship.is_primary.is_(True),
            ))
            old = current.country_code if current else None
            if code is None:
                if current is not None:
                    self.session.delete(current)
                return old, "citizenship", current.id if current else None
            matching = self.session.scalar(select(cm.PersonCitizenship).where(
                cm.PersonCitizenship.person_id == applicant.id,
                cm.PersonCitizenship.country_code == code,
            ))
            if current is not None and current is not matching:
                current.is_primary = False
            if matching is None:
                matching = cm.PersonCitizenship(
                    person_id=applicant.id, country_code=code,
                    citizenship_type="citizen", is_primary=True, sort_order=0,
                )
                self.session.add(matching)
            else:
                matching.is_primary = True
                matching.sort_order = 0
            self.session.flush()
            return old, "citizenship", matching.id
        if path == "applicant.current_residence.country_code":
            if app is None:
                raise DomainValidationError("canonical application is unavailable")
            residence = self.session.scalar(select(cm.ApplicantResidence).where(
                cm.ApplicantResidence.application_id == app.id,
                cm.ApplicantResidence.is_current.is_(True),
            ))
            old = residence.country_code if residence else None
            code = normalize_country(value).code if value is not None else None
            if code is None:
                if residence is not None: self.session.delete(residence)
                return old, "applicant_residence", residence.id if residence else None
            if residence is None:
                residence = cm.ApplicantResidence(application_id=app.id, country_code=code, is_current=True)
                self.session.add(residence); self.session.flush()
            else:
                residence.country_code = code
            return old, "applicant_residence", residence.id
        if path.startswith("applicant.passport."):
            if app is None or applicant is None:
                raise DomainValidationError("canonical applicant passport is unavailable")
            passport = self.session.scalar(select(cm.TravelDocument).where(
                cm.TravelDocument.application_id == app.id,
                cm.TravelDocument.document_type == "passport",
                cm.TravelDocument.is_primary.is_(True),
            ))
            values = {item.field_path: item.value_json for item in payload.decisions}
            if passport is None:
                number = values.get("applicant.passport.number")
                issuer = values.get("applicant.passport.issuing_country_code")
                if not number or not issuer:
                    raise DomainValidationError("passport number and issuing country must be saved together")
                passport = cm.TravelDocument(
                    application_id=app.id, person_id=applicant.id, document_type="passport",
                    number=str(number).strip(), issuing_country_code=normalize_country(issuer).code,
                    is_primary=True, sort_order=0,
                )
                self.session.add(passport); self.session.flush()
            attr = path.rsplit(".", 1)[1]
            old = getattr(passport, attr)
            normalized = (date.fromisoformat(str(value)) if value is not None else None) if attr in {"issue_date", "expiry_date"} else (
                normalize_country(value).code if attr == "issuing_country_code" and value is not None else
                (value.strip() if isinstance(value, str) else value)
            )
            setattr(passport, attr, normalized)
            self.session.flush()
            return old.isoformat() if isinstance(old, date) else old, "travel_document", passport.id
        if path.startswith("applicant.residential_address."):
            if app is None:
                raise DomainValidationError("canonical application is unavailable")
            address = self.session.scalar(select(cm.Address).where(
                cm.Address.application_id == app.id, cm.Address.context == "residential",
                cm.Address.owner_id == app.id,
            ))
            if address is None:
                address = cm.Address(application_id=app.id, context="residential", owner_id=app.id)
                self.session.add(address); self.session.flush()
            attr = path.rsplit(".", 1)[1]
            old = getattr(address, attr)
            normalized = normalize_country(value).code if attr == "country_code" and value is not None else (
                value.strip() if isinstance(value, str) else value
            )
            setattr(address, attr, normalized)
            address.review_state = "confirmed"
            return old, "address", address.id
        if path == "application.mailing_same_as_residential":
            if app is None: raise DomainValidationError("canonical application is unavailable")
            old = app.mailing_same_as_residential
            app.mailing_same_as_residential = value
            return old, "application", app.id
        if path == "application.official_application_date":
            if app is None: raise DomainValidationError("canonical application is unavailable")
            old = app.official_application_date
            app.official_application_date = date.fromisoformat(str(value)) if value is not None else None
            app.application_date_review_state = "confirmed" if value is not None else "needs_review"
            return old.isoformat() if old else None, "application", app.id
        if path in {"contact.email", "contact.phone"}:
            if applicant is None:
                raise DomainValidationError("canonical applicant is unavailable")
            contact_type = path.rsplit(".", 1)[1]
            contact = self.session.scalar(select(cm.ContactPoint).where(
                cm.ContactPoint.person_id == applicant.id,
                cm.ContactPoint.type == contact_type,
                cm.ContactPoint.is_primary.is_(True),
            ))
            old = contact.value if contact else None
            if value is None:
                if contact is not None:
                    self.session.delete(contact)
                return old, "contact", contact.id if contact else None
            if contact is None:
                contact = cm.ContactPoint(
                    person_id=applicant.id, type=contact_type, value=value.strip(),
                    purpose="primary", is_primary=True, sort_order=0,
                )
                self.session.add(contact)
                self.session.flush()
            else:
                contact.value = value.strip()
            return old, "contact", contact.id
        if path == "trip.purpose":
            if app is None:
                raise DomainValidationError("canonical application is unavailable")
            trip = self.session.scalar(select(cm.TripPlan).where(cm.TripPlan.application_id == app.id))
            if trip is None:
                trip = cm.TripPlan(application_id=app.id)
                self.session.add(trip)
                self.session.flush()
            old = trip.intake_purpose_text
            trip.intake_purpose_text = value.strip() if value is not None else None
            trip.purpose_review_state = "confirmed" if value is not None else "needs_review"
            case.purpose = value.strip()[:128] if value is not None else "To be confirmed"
            return old, "trip_plan", trip.id
        if path.startswith("trip.") and path in {
            "trip.imm5257_purpose_code", "trip.arrival_date", "trip.departure_date",
            "trip.available_funds_amount", "trip.available_funds_currency", "trip.funds_source_reference",
        }:
            if app is None: raise DomainValidationError("canonical application is unavailable")
            trip = self.session.scalar(select(cm.TripPlan).where(cm.TripPlan.application_id == app.id))
            if trip is None:
                trip = cm.TripPlan(application_id=app.id); self.session.add(trip); self.session.flush()
            attr = path.removeprefix("trip.")
            old = getattr(trip, attr)
            normalized = date.fromisoformat(str(value)) if value is not None and attr in {"arrival_date", "departure_date"} else (
                value.strip().upper() if isinstance(value, str) and attr == "available_funds_currency" else
                (value.strip() if isinstance(value, str) else value)
            )
            setattr(trip, attr, normalized)
            if attr == "imm5257_purpose_code": trip.purpose_review_state = "confirmed" if value is not None else "needs_review"
            return old.isoformat() if isinstance(old, date) else float(old) if old is not None and attr == "available_funds_amount" else old, "trip_plan", trip.id
        if path in PERSON_REFERENCE_FIELDS:
            if app is None:
                raise DomainValidationError("canonical application is unavailable")
            person = self.session.get(models.Person, uuid.UUID(str(value))) if value is not None else None
            if person is not None and person.case_id != case.id:
                raise DomainValidationError(f"{path} must identify a person in this case")
            if value is not None and person is None:
                raise DomainValidationError(f"{path} must identify a person in this case")
            trip = self.session.scalar(select(cm.TripPlan).where(cm.TripPlan.application_id == app.id))
            if trip is None:
                trip = cm.TripPlan(application_id=app.id)
                self.session.add(trip)
                self.session.flush()
            role = cm.OperationalRole.SPONSOR if path.startswith("sponsor.") else cm.OperationalRole.HOST
            if role == cm.OperationalRole.SPONSOR:
                current = self.session.scalar(select(cm.FundingSource).where(
                    cm.FundingSource.trip_plan_id == trip.id,
                    cm.FundingSource.payer_kind == "sponsor",
                    cm.FundingSource.is_primary.is_(True),
                ))
                old = current.person_id if current else None
                for item in self.session.scalars(select(cm.FundingSource).where(
                    cm.FundingSource.trip_plan_id == trip.id,
                    cm.FundingSource.payer_kind == "sponsor",
                )):
                    self.session.delete(item)
                if person is not None:
                    self.session.add(cm.FundingSource(
                        trip_plan_id=trip.id, payer_kind="sponsor", person_id=person.id,
                        is_primary=True, sort_order=0,
                    ))
            else:
                current = self.session.scalar(select(cm.HostRecord).where(
                    cm.HostRecord.trip_plan_id == trip.id,
                    cm.HostRecord.is_primary.is_(True),
                ))
                old = current.person_id if current and current.host_type == "person" else None
                for item in self.session.scalars(select(cm.HostRecord).where(cm.HostRecord.trip_plan_id == trip.id)):
                    self.session.delete(item)
                if person is not None:
                    self.session.add(cm.HostRecord(
                        trip_plan_id=trip.id, host_type="person", person_id=person.id,
                        is_primary=True, sort_order=0,
                    ))
            affected = list(self.session.scalars(select(models.Person).where(models.Person.case_id == case.id)))
            self.session.execute(delete(cm.CasePersonRole).where(
                cm.CasePersonRole.case_id == case.id, cm.CasePersonRole.role == role,
            ))
            if person is not None:
                add_authoritative_role(self.session, person, role, assigned_by=payload.reviewed_by)
            for affected_person in affected:
                roles = list(self.session.scalars(select(cm.CasePersonRole.role).where(
                    cm.CasePersonRole.person_id == affected_person.id
                )))
                affected_person.roles = list(dict.fromkeys(roles)) or [cm.OperationalRole.OTHER.value]
            return str(old) if old else None, "person", person.id if person else None
        if path in FACT_FIELDS:
            current = self.session.scalar(select(models.Fact).where(
                models.Fact.case_id == case.id,
                models.Fact.key == path,
                models.Fact.status == "confirmed",
            ).order_by(models.Fact.created_at.desc(), models.Fact.id.desc()))
            old = current.value_json if current else None
            for fact in self.session.scalars(select(models.Fact).where(
                models.Fact.case_id == case.id,
                models.Fact.key == path,
                models.Fact.status == "confirmed",
            )):
                fact.status = "rejected"
            fact = models.Fact(
                case_id=case.id, person_id=None, key=path, value_json=value,
                source_type={
                    "employee_manual": "manual",
                    "commercial_message": "whatsapp",
                    "google_forms_csv": "google_form",
                }[payload.source_type],
                source_reference=payload.source_reference,
                confidence=1.0 if value is not None else None,
                status="confirmed" if value is not None else "proposed",
            )
            self.session.add(fact)
            self.session.flush()
            return old, "fact", fact.id
        raise DomainValidationError(f"unsupported canonical field: {path}")

    def list_revisions(self, case_id):
        if self.session.get(models.Case, case_id) is None:
            raise DomainNotFound("Case not found")
        return list(self.session.scalars(select(models.CanonicalValueRevision).where(
            models.CanonicalValueRevision.case_id == case_id
        ).order_by(models.CanonicalValueRevision.created_at.desc(), models.CanonicalValueRevision.id.desc())))


class DynamicCaseService:
    def __init__(self, session: Session):
        self.session = session

    def status(self, case_id: uuid.UUID) -> dict[str, Any]:
        case = self.session.get(models.Case, case_id)
        if case is None:
            raise DomainNotFound("Case not found")
        readiness = CanadaPreparationReadinessService(self.session).evaluate(case_id)
        issues: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add(issue_key, category, code, field_path, severity, title, message, action, source_type, source_id=None):
            if issue_key in seen:
                return
            seen.add(issue_key)
            issues.append({
                "issue_key": issue_key, "category": category, "code": code,
                "field_path": field_path, "severity": severity, "title": title,
                "message": message, "action": action, "source_type": source_type,
                "source_id": source_id,
            })

        for item in readiness.issues:
            add(f"readiness:{item.code}:{item.path}", "canonical", item.code, item.path,
                item.severity, item.label, item.message, item.action, "readiness")
        for item in self.session.scalars(select(models.FactExtractionCandidate).where(
            models.FactExtractionCandidate.case_id == case_id,
            models.FactExtractionCandidate.status.in_((models.FactCandidateStatus.PROPOSED, models.FactCandidateStatus.CONFLICT)),
        )):
            add(f"fact-candidate:{item.id}", "evidence", "unresolved_candidate", item.key,
                "blocking" if item.status == models.FactCandidateStatus.CONFLICT else "warning",
                f"Review {item.key}", "Commercial message evidence awaits review.",
                "Confirm, correct, or reject the candidate.", "commercial_message", item.id)
        for item in self.session.scalars(select(models.Task).where(
            models.Task.case_id == case_id, models.Task.status.in_(("open", "in_progress"))
        )):
            add(f"task:{item.id}", "task", "open_task", None,
                "blocking" if item.blocking else "warning", item.title, item.description,
                "Complete or resolve the task.", "task", item.id)
        for key, label in (("sponsor.exists", "Financial sponsor"), ("host.exists", "Host in Canada")):
            if self._fact(case_id, key) is None:
                add(f"decision:{key}", "decision", "unresolved_decision", key, "blocking",
                    label, f"{label} is unknown.", "Confirm yes or no.", "canonical")
        values = self.current_values(case_id, case)
        for exists_key, person_key, label in (
            ("sponsor.exists", "sponsor.person_id", "Sponsor identity"),
            ("host.exists", "host.person_id", "Host identity"),
        ):
            if values.get(exists_key) is True and values.get(person_key) is None:
                add(f"decision:{person_key}", "decision", "missing_party_identity", person_key, "blocking",
                    label, f"{label} is not selected.", "Select the known person.", "canonical")

        pending_documents = list(self.session.scalars(select(models.Requirement).where(
            models.Requirement.case_id == case_id, models.Requirement.active.is_(True),
            models.Requirement.is_blocking.is_(True),
            models.Requirement.fulfillment_status == models.RequirementFulfillmentStatus.PENDING,
        )))
        remediation_issues = list(self.session.scalars(
            select(models.DocumentRemediationIssue)
            .join(models.Document)
            .where(
                models.Document.case_id == case_id,
                models.DocumentRemediationIssue.status == "open",
            )
        ))
        for item in remediation_issues:
            add(
                f"document-remediation:{item.id}",
                "document",
                item.problem_type,
                "documents",
                "blocking",
                "Document review required",
                item.explanation,
                item.correction,
                "document_pipeline",
                item.id,
            )
        conflicts = [item for item in issues if item["severity"] == "blocking"]
        has_activity = bool(
            case.workflow_state != models.WorkflowState.INTAKE
            or self.session.scalar(select(func.count(models.Person.id)).where(models.Person.case_id == case_id))
            or self.session.scalar(select(func.count(models.Fact.id)).where(models.Fact.case_id == case_id))
            or self.session.scalar(select(func.count(models.Document.id)).where(models.Document.case_id == case_id))
            or self.session.scalar(select(func.count(models.ConversationImport.id)).where(models.ConversationImport.case_id == case_id))
            or self.session.scalar(select(func.count(cm.CanadaLegacyImportRun.id)).where(cm.CanadaLegacyImportRun.case_id == case_id))
        )
        stage = {
            models.WorkflowState.REVIEW: "FINAL_REVIEW",
            models.WorkflowState.READY: "READY",
            models.WorkflowState.SUBMITTED: "SUBMITTED",
        }.get(case.workflow_state, "ACTIVE" if has_activity else "NEW")
        intake_ready = bool(values.get("case.visa_type") and values.get("applicant.given_names")
                            and values.get("applicant.family_name") and values.get("trip.purpose")
                            and values.get("destination.country_code") and values.get("trip.payer")
                            and values.get("sponsor.exists") is not None and values.get("host.exists") is not None
                            and (values.get("sponsor.exists") is not True or values.get("sponsor.person_id"))
                            and (values.get("host.exists") is not True or values.get("host.person_id")))
        return {
            "case_id": case_id, "lifecycle_stage": stage,
            "legacy_workflow_state": case.workflow_state,
            "can_enter_final_review": readiness.ready and not conflicts,
            "canonical_values": values,
            "dimensions": [
                {"key": "intake", "ready": intake_ready, "blocking_count": 0 if intake_ready else 1, "warning_count": 0},
                {"key": "canonical", "ready": readiness.blocking_count == 0, "blocking_count": readiness.blocking_count, "warning_count": readiness.warning_count},
                {"key": "documents", "ready": not pending_documents and not remediation_issues, "blocking_count": len(pending_documents) + len(remediation_issues), "warning_count": 0},
                {"key": "issues", "ready": not conflicts, "blocking_count": len(conflicts), "warning_count": len(issues) - len(conflicts)},
            ],
            "issues": issues,
        }

    def _fact(self, case_id, key):
        return self.session.scalar(select(models.Fact).where(
            models.Fact.case_id == case_id, models.Fact.key == key,
            models.Fact.status == "confirmed",
        ).order_by(models.Fact.created_at.desc(), models.Fact.id.desc()))

    def current_values(self, case_id, case=None):
        case = case or self.session.get(models.Case, case_id)
        app = self.session.scalar(select(cm.CanadaApplication).where(cm.CanadaApplication.case_id == case_id))
        applicant = self.session.get(models.Person, app.applicant_person_id) if app and app.applicant_person_id else None
        trip = self.session.scalar(select(cm.TripPlan).where(cm.TripPlan.application_id == app.id)) if app else None
        contacts = {}
        biography = self.session.get(cm.PersonBiography, applicant.id) if applicant else None
        if applicant:
            for item in self.session.scalars(select(cm.ContactPoint).where(
                cm.ContactPoint.person_id == applicant.id, cm.ContactPoint.is_primary.is_(True)
            )):
                contacts[item.type] = item.value
        values = {
            "case.visa_type": case.visa_type,
            "applicant.given_names": applicant.first_name if applicant else None,
            "applicant.family_name": applicant.last_name if applicant else None,
            "applicant.biography.date_of_birth": biography.date_of_birth.isoformat() if biography and biography.date_of_birth else None,
            "applicant.biography.other_names": biography.other_names if biography else None,
            "applicant.biography.sex": biography.sex if biography else None,
            "applicant.biography.birth_city": biography.birth_city if biography else None,
            "applicant.biography.birth_state_province": biography.birth_state_province if biography else None,
            "applicant.biography.birth_country_code": biography.birth_country_code if biography else None,
            "applicant.biography.marital_status": biography.marital_status if biography else None,
            "contact.email": contacts.get("email"), "contact.phone": contacts.get("phone"),
            "trip.purpose": trip.intake_purpose_text if trip else None,
            "application.mailing_same_as_residential": app.mailing_same_as_residential if app else None,
            "application.official_application_date": app.official_application_date.isoformat() if app and app.official_application_date else None,
            "trip.imm5257_purpose_code": trip.imm5257_purpose_code if trip else None,
            "trip.arrival_date": trip.arrival_date.isoformat() if trip and trip.arrival_date else None,
            "trip.departure_date": trip.departure_date.isoformat() if trip and trip.departure_date else None,
            "trip.available_funds_amount": float(trip.available_funds_amount) if trip and trip.available_funds_amount is not None else None,
            "trip.available_funds_currency": trip.available_funds_currency if trip else None,
            "trip.funds_source_reference": trip.funds_source_reference if trip else None,
        }
        residence = self.session.scalar(select(cm.ApplicantResidence).where(
            cm.ApplicantResidence.application_id == app.id, cm.ApplicantResidence.is_current.is_(True),
        )) if app else None
        values["applicant.current_residence.country_code"] = residence.country_code if residence else None
        passport = self.session.scalar(select(cm.TravelDocument).where(
            cm.TravelDocument.application_id == app.id, cm.TravelDocument.document_type == "passport",
            cm.TravelDocument.is_primary.is_(True),
        )) if app else None
        for field in ("number", "issuing_country_code", "issue_date", "expiry_date"):
            current = getattr(passport, field) if passport else None
            values[f"applicant.passport.{field}"] = current.isoformat() if isinstance(current, date) else current
        address = self.session.scalar(select(cm.Address).where(
            cm.Address.application_id == app.id, cm.Address.context == "residential", cm.Address.owner_id == app.id,
        )) if app else None
        for field in ("street_number", "street_name", "city", "state_province", "postal_code", "country_code"):
            values[f"applicant.residential_address.{field}"] = getattr(address, field) if address else None
        funding = self.session.scalar(select(cm.FundingSource).where(
            cm.FundingSource.trip_plan_id == trip.id,
            cm.FundingSource.payer_kind == "sponsor",
            cm.FundingSource.is_primary.is_(True),
        )) if trip else None
        host = self.session.scalar(select(cm.HostRecord).where(
            cm.HostRecord.trip_plan_id == trip.id, cm.HostRecord.is_primary.is_(True),
        )) if trip else None
        values["sponsor.person_id"] = str(funding.person_id) if funding and funding.person_id else None
        values["host.person_id"] = str(host.person_id) if host and host.host_type == "person" and host.person_id else None
        primary_citizenship = self.session.scalar(select(cm.PersonCitizenship).where(
            cm.PersonCitizenship.person_id == applicant.id,
            cm.PersonCitizenship.is_primary.is_(True),
        )) if applicant else None
        values["applicant.citizenship.primary"] = primary_citizenship.country_code if primary_citizenship else None
        for key in FACT_FIELDS:
            fact = self._fact(case_id, key)
            values[key] = fact.value_json if fact else None
        return values
