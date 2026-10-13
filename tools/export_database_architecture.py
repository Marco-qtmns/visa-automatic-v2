"""Export the authoritative ORM schema and architecture contract as JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql

from backend.app.database import Base
from backend.app.models import *  # noqa: F401,F403


REVISION = "0002_record_lifecycle"
DOMAINS = {
    "core_case_audit": [
        "cases", "persons", "case_person_roles", "facts",
        "canonical_value_revisions", "tasks", "workflow_transitions",
        "application_audit_events",
    ],
    "authentication": [
        "auth_users", "auth_sessions", "auth_mfa_challenges",
        "auth_login_throttles", "auth_security_events",
    ],
    "intake_evidence": [
        "intake_submissions", "intake_processing_attempts",
        "canada_legacy_import_runs", "canada_import_candidates",
        "legacy_import_entity_links", "field_provenance_reviews",
        "conversation_imports", "conversation_messages", "fact_extraction_runs",
        "fact_extraction_candidates",
    ],
    "canada_application": [
        "canada_applications", "person_biographies", "person_citizenships",
        "person_identifiers", "contact_points", "canada_addresses",
        "applicant_residences", "travel_documents", "trip_plans",
        "canada_organizations", "funding_sources", "host_records",
        "family_relationships", "education_records", "activity_records",
        "residence_history_records", "travel_history_records",
        "official_application_answers", "official_explanations",
        "representative_profiles", "representative_profile_revisions",
        "representative_authorizations",
    ],
    "documents_requirements": [
        "documents", "document_processing_attempts", "document_remediation_issues",
        "document_classifications", "document_quality_checks", "requirements",
        "requirement_document_matches", "requirement_completeness_evaluations",
        "requirement_fulfillment_events",
    ],
    "preparation_approvals": [
        "preparation_runs", "preparation_artifacts", "preparation_approvals",
    ],
}


def _expression(value: object | None) -> str | None:
    if value is None:
        return None
    argument = getattr(value, "arg", value)
    if callable(argument):
        return getattr(argument, "__name__", type(argument).__name__)
    return str(argument)


def _constraint(item: object) -> dict[str, object]:
    result: dict[str, object] = {"name": getattr(item, "name", None)}
    if isinstance(item, PrimaryKeyConstraint):
        result.update(type="primary_key", columns=[column.name for column in item.columns])
    elif isinstance(item, ForeignKeyConstraint):
        result.update(
            type="foreign_key",
            columns=[element.parent.name for element in item.elements],
            references=[element.target_fullname for element in item.elements],
            on_delete=item.ondelete,
            on_update=item.onupdate,
        )
    elif isinstance(item, UniqueConstraint):
        result.update(type="unique", columns=[column.name for column in item.columns])
    elif isinstance(item, CheckConstraint):
        result.update(type="check", expression=str(item.sqltext))
    else:  # pragma: no cover - exporter fails visibly on a newly introduced kind
        result.update(type=type(item).__name__)
    return result


def architecture() -> dict[str, object]:
    dialect = postgresql.dialect()
    tables: list[dict[str, object]] = []
    relationships: list[dict[str, object]] = []
    domain_by_table = {
        table_name: domain
        for domain, table_names in DOMAINS.items()
        for table_name in table_names
    }
    for table in sorted(Base.metadata.tables.values(), key=lambda value: value.name):
        constraints = sorted(
            (_constraint(item) for item in table.constraints),
            key=lambda item: (str(item["type"]), str(item["name"]), str(item)),
        )
        for item in constraints:
            if item["type"] == "foreign_key":
                relationships.append({
                    "from_table": table.name,
                    "from_columns": item["columns"],
                    "to_table": str(item["references"][0]).split(".", 1)[0],
                    "to_columns": [str(value).split(".", 1)[1] for value in item["references"]],
                    "on_delete": item["on_delete"],
                })
        tables.append({
            "name": table.name,
            "domain": domain_by_table[table.name],
            "columns": [
                {
                    "name": column.name,
                    "postgresql_type": column.type.compile(dialect=dialect),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "autoincrement": column.autoincrement,
                    "python_default": _expression(column.default),
                    "server_default": _expression(column.server_default),
                }
                for column in table.columns
            ],
            "constraints": constraints,
            "indexes": [
                {
                    "name": index.name,
                    "columns": [getattr(expression, "name", str(expression)) for expression in index.expressions],
                    "unique": index.unique,
                    "postgresql_where": _expression(index.dialect_options["postgresql"].get("where")),
                }
                for index in sorted(table.indexes, key=lambda value: value.name or "")
            ],
        })
    return {
        "format_version": 1,
        "schema_source": "backend.app.database.Base.metadata",
        "baseline_revision": REVISION,
        "database_engine": "PostgreSQL 17",
        "table_count": len(tables),
        "domains": DOMAINS,
        "authority": {
            "case_identity": ["cases"],
            "operational_person_roles": ["case_person_roles"],
            "canada_application_values": ["canada_applications", "typed_canada_child_tables"],
            "defined_fact_decisions": ["facts"],
            "canonical_history": ["canonical_value_revisions"],
            "source_evidence_not_authoritative": [
                "intake_submissions", "canada_import_candidates",
                "conversation_messages", "fact_extraction_candidates", "documents",
            ],
            "generated_packages": ["preparation_runs", "preparation_artifacts"],
            "approvals": ["preparation_approvals"],
        },
        "tables": tables,
        "relationships": sorted(
            relationships,
            key=lambda item: (str(item["from_table"]), str(item["from_columns"])),
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(architecture(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
