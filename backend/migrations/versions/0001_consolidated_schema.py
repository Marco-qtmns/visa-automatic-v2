"""consolidated Visa Automatic schema baseline

Revision ID: 0001_consolidated_schema
Revises: none
Create Date: 2026-10-13

This file is an immutable schema snapshot.  It deliberately does not import
the application ORM metadata.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_consolidated_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('auth_login_throttles',
    sa.Column('key_hash', sa.String(length=64), nullable=False),
    sa.Column('failed_attempts', sa.Integer(), nullable=False),
    sa.Column('window_started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('key_hash')
    )
    op.create_table('auth_users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('display_name', sa.String(length=200), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('role', sa.String(length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('mfa_enabled', sa.Boolean(), nullable=False),
    sa.Column('mfa_secret_encrypted', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_successful_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("role IN ('ADMIN', 'CASE_WORKER', 'REVIEWER')", name='ck_auth_users_role'),
    sa.CheckConstraint('email = lower(email)', name='ck_auth_users_normalized_email'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('cases',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_number', sa.String(length=64), nullable=False),
    sa.Column('visa_type', sa.String(length=64), nullable=False),
    sa.Column('purpose', sa.String(length=128), nullable=False),
    sa.Column('workflow_state', sa.Enum('INTAKE', 'DOCUMENTS', 'PREPARE', 'REVIEW', 'READY', 'SUBMITTED', name='workflow_state', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_number')
    )
    op.create_table('representative_profiles',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('profile_name', sa.String(length=255), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('profile_name')
    )
    op.create_table('application_audit_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('actor_role', sa.String(length=32), nullable=True),
    sa.Column('action', sa.String(length=96), nullable=False),
    sa.Column('target_entity_type', sa.String(length=64), nullable=False),
    sa.Column('target_entity_id', sa.String(length=64), nullable=True),
    sa.Column('case_id', sa.Uuid(), nullable=True),
    sa.Column('outcome', sa.String(length=24), nullable=False),
    sa.Column('metadata_json', sa.JSON(), nullable=False),
    sa.Column('request_id', sa.String(length=64), nullable=True),
    sa.ForeignKeyConstraint(['actor_user_id'], ['auth_users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_application_audit_events_case_created', 'application_audit_events', ['case_id', 'created_at'], unique=False)
    op.create_index('ix_application_audit_events_created_at', 'application_audit_events', ['created_at'], unique=False)
    op.create_table('auth_mfa_challenges',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('purpose', sa.String(length=24), nullable=False),
    sa.Column('pending_secret_encrypted', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failed_attempts', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['auth_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_auth_mfa_challenges_user_id', 'auth_mfa_challenges', ['user_id'], unique=False)
    op.create_table('auth_security_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('subject_hash', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['auth_users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_auth_security_events_created_at', 'auth_security_events', ['created_at'], unique=False)
    op.create_table('auth_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('csrf_token_hash', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['auth_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'], unique=False)
    op.create_table('canada_legacy_import_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('source_type', sa.String(length=40), nullable=False),
    sa.Column('source_identifier', sa.String(length=255), nullable=False),
    sa.Column('source_hash', sa.String(length=64), nullable=False),
    sa.Column('mapping_version', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('imported_by', sa.String(length=255), nullable=True),
    sa.Column('counts_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('warnings_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('error_summary', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("source_type IN ('google_verified_csv', 'canada_case_json', 'representative_profile_json')", name='canada_import_source_type_valid'),
    sa.CheckConstraint("status IN ('previewed', 'reviewing', 'applied', 'failed')", name='canada_import_status_valid'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'source_type', 'source_hash', 'mapping_version', name='uq_canada_import_source')
    )
    op.create_index(op.f('ix_canada_legacy_import_runs_case_id'), 'canada_legacy_import_runs', ['case_id'], unique=False)
    op.create_table('canada_organizations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=True),
    sa.Column('legal_name', sa.String(length=255), nullable=False),
    sa.Column('organization_type', sa.String(length=64), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=64), nullable=True),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_canada_organizations_case_id'), 'canada_organizations', ['case_id'], unique=False)
    op.create_table('canonical_value_revisions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('field_path', sa.String(length=255), nullable=False),
    sa.Column('entity_type', sa.String(length=64), nullable=False),
    sa.Column('entity_id', sa.Uuid(), nullable=True),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('original_value_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('value_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('source_type', sa.String(length=64), nullable=False),
    sa.Column('source_reference', sa.Text(), nullable=False),
    sa.Column('source_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('source_version', sa.String(length=64), nullable=True),
    sa.Column('review_state', sa.String(length=24), nullable=False),
    sa.Column('reviewed_by', sa.String(length=255), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='canonical_value_revision_review_state_valid'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'field_path', 'revision', name='uq_canonical_value_revision')
    )
    op.create_index('ix_canonical_value_revisions_case_field', 'canonical_value_revisions', ['case_id', 'field_path'], unique=False)
    op.create_table('conversation_imports',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('source_type', sa.Enum('whatsapp_paste', 'whatsapp_export', name='conversation_source_type', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('original_filename', sa.String(length=512), nullable=True),
    sa.Column('imported_by', sa.String(length=255), nullable=True),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=False),
    sa.Column('parse_status', sa.Enum('parsed', 'parsed_with_warnings', 'failed', name='conversation_parse_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('parse_warnings_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('message_count', sa.Integer(), nullable=False),
    sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'content_hash', name='uq_conversation_import_content')
    )
    op.create_index('ix_conversation_imports_case_id', 'conversation_imports', ['case_id'], unique=False)
    op.create_table('field_provenance_reviews',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('entity_type', sa.String(length=64), nullable=False),
    sa.Column('entity_id', sa.Uuid(), nullable=False),
    sa.Column('field_key', sa.String(length=128), nullable=False),
    sa.Column('source_type', sa.String(length=32), nullable=False),
    sa.Column('source_reference', sa.Text(), nullable=False),
    sa.Column('source_digest', sa.String(length=64), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('review_state', sa.String(length=24), nullable=False),
    sa.Column('reviewed_by', sa.String(length=255), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("entity_type IN ('person', 'application', 'person_biography', 'address', 'residence', 'travel_document', 'trip_plan', 'funding_source', 'host', 'family_relationship', 'education', 'activity', 'residence_history', 'travel_history', 'official_answer', 'official_explanation', 'representative_authorization')", name='field_provenance_entity_type_valid'),
    sa.CheckConstraint("review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='field_provenance_review_state_valid'),
    sa.CheckConstraint('confidence IS NULL OR (confidence >= 0 AND confidence <= 1)', name='field_provenance_confidence_range'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_field_provenance_reviews_case_id'), 'field_provenance_reviews', ['case_id'], unique=False)
    op.create_index('ix_field_provenance_subject', 'field_provenance_reviews', ['entity_type', 'entity_id', 'field_key'], unique=False)
    op.create_table('persons',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('first_name', sa.String(length=128), nullable=False),
    sa.Column('last_name', sa.String(length=128), nullable=False),
    sa.Column('roles', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_persons_case_id', 'persons', ['case_id'], unique=False)
    op.create_table('preparation_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('initiated_by', sa.String(length=255), nullable=False),
    sa.Column('payload_schema_version', sa.String(length=32), nullable=False),
    sa.Column('preparation_policy_version', sa.String(length=32), nullable=False),
    sa.Column('payload_hash', sa.String(length=64), nullable=False),
    sa.Column('adapter_version', sa.String(length=32), nullable=False),
    sa.Column('generator_version', sa.String(length=128), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_code', sa.String(length=64), nullable=True),
    sa.Column('error_summary', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('running', 'succeeded', 'failed')", name='preparation_run_status_valid'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'case_id', 'payload_hash', name='uq_preparation_run_identity'),
    sa.UniqueConstraint('id', 'case_id', name='uq_preparation_run_case_identity')
    )
    op.create_index('ix_preparation_runs_case_created', 'preparation_runs', ['case_id', 'created_at'], unique=False)
    op.create_index('uq_preparation_running_case', 'preparation_runs', ['case_id'], unique=True, postgresql_where=sa.text("status = 'running'"), sqlite_where=sa.text("status = 'running'"))
    op.create_table('representative_profile_revisions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('profile_id', sa.Uuid(), nullable=False),
    sa.Column('revision_number', sa.Integer(), nullable=False),
    sa.Column('family_name', sa.String(length=128), nullable=False),
    sa.Column('given_names', sa.String(length=128), nullable=False),
    sa.Column('organization_name', sa.String(length=255), nullable=True),
    sa.Column('unit', sa.String(length=64), nullable=True),
    sa.Column('street_number', sa.String(length=64), nullable=True),
    sa.Column('street_name', sa.String(length=255), nullable=True),
    sa.Column('city', sa.String(length=128), nullable=True),
    sa.Column('province', sa.String(length=128), nullable=True),
    sa.Column('country_code', sa.String(length=3), nullable=True),
    sa.Column('postal_code', sa.String(length=32), nullable=True),
    sa.Column('phone_country_code', sa.String(length=8), nullable=True),
    sa.Column('phone_number', sa.String(length=64), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('category', sa.String(length=128), nullable=True),
    sa.Column('membership_number', sa.String(length=128), nullable=True),
    sa.Column('membership_province', sa.String(length=128), nullable=True),
    sa.Column('other_category_details', sa.Text(), nullable=True),
    sa.Column('supervising_lawyer', sa.String(length=255), nullable=True),
    sa.Column('supervising_lawyer_membership', sa.String(length=128), nullable=True),
    sa.Column('created_by', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['representative_profiles.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('profile_id', 'revision_number', name='uq_representative_profile_revision')
    )
    op.create_index(op.f('ix_representative_profile_revisions_profile_id'), 'representative_profile_revisions', ['profile_id'], unique=False)
    op.create_table('workflow_transitions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('from_state', sa.Enum('INTAKE', 'DOCUMENTS', 'PREPARE', 'REVIEW', 'READY', 'SUBMITTED', name='workflow_transition_from_state', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('to_state', sa.Enum('INTAKE', 'DOCUMENTS', 'PREPARE', 'REVIEW', 'READY', 'SUBMITTED', name='workflow_transition_to_state', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('actor', sa.String(length=255), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_transitions_case_id', 'workflow_transitions', ['case_id'], unique=False)
    op.create_table('canada_applications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('applicant_person_id', sa.Uuid(), nullable=True),
    sa.Column('legal_guardian_person_id', sa.Uuid(), nullable=True),
    sa.Column('official_application_date', sa.Date(), nullable=True),
    sa.Column('application_date_review_state', sa.String(length=24), nullable=False),
    sa.Column('native_language_code', sa.String(length=32), nullable=True),
    sa.Column('preferred_language_code', sa.String(length=32), nullable=True),
    sa.Column('service_language_code', sa.String(length=32), nullable=True),
    sa.Column('mailing_same_as_residential', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("application_date_review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='canada_application_date_review_state_valid'),
    sa.ForeignKeyConstraint(['applicant_person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['legal_guardian_person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('applicant_person_id'),
    sa.UniqueConstraint('case_id')
    )
    op.create_table('canada_import_candidates',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('import_run_id', sa.Uuid(), nullable=False),
    sa.Column('domain_section', sa.String(length=40), nullable=False),
    sa.Column('employee_label', sa.String(length=255), nullable=False),
    sa.Column('target_entity_type', sa.String(length=64), nullable=False),
    sa.Column('target_entity_id', sa.Uuid(), nullable=True),
    sa.Column('target_field', sa.String(length=128), nullable=False),
    sa.Column('operation', sa.String(length=32), nullable=False),
    sa.Column('source_path', sa.String(length=255), nullable=False),
    sa.Column('source_record_key', sa.String(length=255), nullable=False),
    sa.Column('source_classification', sa.String(length=40), nullable=False),
    sa.Column('source_reference', sa.Text(), nullable=False),
    sa.Column('raw_value_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('proposed_value_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('current_value_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('conflict_type', sa.String(length=64), nullable=True),
    sa.Column('review_policy', sa.String(length=40), nullable=False),
    sa.Column('conflict_policy', sa.String(length=40), nullable=False),
    sa.Column('reviewed_by', sa.String(length=255), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('canonical_review_state', sa.String(length=24), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("canonical_review_state IS NULL OR canonical_review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='canada_import_candidate_review_state_valid'),
    sa.CheckConstraint("source_classification IN ('applicant_direct', 'legacy_staff_review', 'legacy_derived', 'representative_profile', 'legacy_narrative_derived')", name='canada_import_source_class_valid'),
    sa.CheckConstraint("status IN ('new', 'same', 'conflict', 'ambiguous', 'accepted', 'rejected', 'applied')", name='canada_import_candidate_status_valid'),
    sa.ForeignKeyConstraint(['import_run_id'], ['canada_legacy_import_runs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('import_run_id', 'source_path', 'source_record_key', 'target_entity_type', 'target_field', name='uq_canada_import_candidate')
    )
    op.create_index(op.f('ix_canada_import_candidates_import_run_id'), 'canada_import_candidates', ['import_run_id'], unique=False)
    op.create_table('case_person_roles',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=24), nullable=False),
    sa.Column('assigned_by', sa.String(length=255), nullable=True),
    sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("role IN ('applicant', 'representative', 'sponsor', 'host', 'other')", name='case_person_role_valid'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'person_id', 'role', name='uq_case_person_operational_role')
    )
    op.create_index(op.f('ix_case_person_roles_case_id'), 'case_person_roles', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_person_roles_person_id'), 'case_person_roles', ['person_id'], unique=False)
    op.create_index('uq_case_one_applicant_role', 'case_person_roles', ['case_id'], unique=True, postgresql_where=sa.text("role = 'applicant'"), sqlite_where=sa.text("role = 'applicant'"))
    op.create_index('uq_case_one_representative_role', 'case_person_roles', ['case_id'], unique=True, postgresql_where=sa.text("role = 'representative'"), sqlite_where=sa.text("role = 'representative'"))
    op.create_table('contact_points',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.String(length=16), nullable=False),
    sa.Column('value', sa.String(length=255), nullable=False),
    sa.Column('country_code', sa.String(length=8), nullable=True),
    sa.Column('purpose', sa.String(length=32), nullable=False),
    sa.Column('is_primary', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.CheckConstraint("type IN ('email', 'phone')", name='contact_point_type_valid'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('person_id', 'type', 'purpose', 'sort_order', name='uq_person_contact_order')
    )
    op.create_index(op.f('ix_contact_points_person_id'), 'contact_points', ['person_id'], unique=False)
    op.create_table('conversation_messages',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('conversation_import_id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('sequence_number', sa.Integer(), nullable=False),
    sa.Column('sender', sa.String(length=255), nullable=True),
    sa.Column('message_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('source_reference', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['conversation_import_id'], ['conversation_imports.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('conversation_import_id', 'sequence_number', name='uq_conversation_message_sequence')
    )
    op.create_index('ix_conversation_messages_case_id', 'conversation_messages', ['case_id'], unique=False)
    op.create_index('ix_conversation_messages_import_id', 'conversation_messages', ['conversation_import_id'], unique=False)
    op.create_table('documents',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=True),
    sa.Column('document_type', sa.String(length=128), nullable=True),
    sa.Column('original_filename', sa.String(length=512), nullable=False),
    sa.Column('storage_path', sa.Text(), nullable=False),
    sa.Column('mime_type', sa.String(length=255), nullable=False),
    sa.Column('source_type', sa.String(length=32), nullable=False),
    sa.Column('classification_status', sa.Enum('unclassified', 'classification_pending', 'suggestion_available', 'confirmed', 'classification_failed', name='document_classification_state', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('quality_status', sa.Enum('not_checked', 'checking', 'passed', 'failed', 'manual_review', 'manual_accepted', 'manual_rejected', 'error', name='document_quality_state', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('metadata_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_case_id', 'documents', ['case_id'], unique=False)
    op.create_table('fact_extraction_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('conversation_import_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Enum('running', 'completed', 'failed', name='fact_extraction_run_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('provider', sa.String(length=64), nullable=False),
    sa.Column('model_version', sa.String(length=128), nullable=True),
    sa.Column('candidate_count', sa.Integer(), nullable=False),
    sa.Column('rejected_output_count', sa.Integer(), nullable=False),
    sa.Column('failure_reason', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['conversation_import_id'], ['conversation_imports.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fact_extraction_runs_created_at', 'fact_extraction_runs', ['created_at'], unique=False)
    op.create_index('ix_fact_extraction_runs_import_id', 'fact_extraction_runs', ['conversation_import_id'], unique=False)
    op.create_table('facts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=True),
    sa.Column('key', sa.String(length=255), nullable=False),
    sa.Column('value_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('source_type', sa.String(length=32), nullable=False),
    sa.Column('source_reference', sa.Text(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_facts_case_id', 'facts', ['case_id'], unique=False)
    op.create_index('ix_facts_case_key', 'facts', ['case_id', 'key'], unique=False)
    op.create_table('intake_submissions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('source_type', sa.String(length=40), nullable=False),
    sa.Column('source_external_id', sa.String(length=255), nullable=True),
    sa.Column('source_filename', sa.String(length=255), nullable=True),
    sa.Column('source_hash', sa.String(length=64), nullable=False),
    sa.Column('source_size_bytes', sa.Integer(), nullable=False),
    sa.Column('raw_source_reference', sa.String(length=255), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('mapping_version', sa.String(length=32), nullable=False),
    sa.Column('processing_status', sa.String(length=24), nullable=False),
    sa.Column('requested_case_id', sa.Uuid(), nullable=True),
    sa.Column('case_id', sa.Uuid(), nullable=True),
    sa.Column('import_run_id', sa.Uuid(), nullable=True),
    sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failure_code', sa.String(length=64), nullable=True),
    sa.Column('failure_message', sa.Text(), nullable=True),
    sa.Column('failure_detail_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('issue_count', sa.Integer(), nullable=False),
    sa.Column('duplicate_receive_count', sa.Integer(), nullable=False),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.CheckConstraint("processing_status IN ('RECEIVED', 'PROCESSING', 'PROCESSED', 'NEEDS_REVIEW', 'FAILED')", name='intake_status_valid'),
    sa.CheckConstraint('duplicate_receive_count >= 0', name='intake_duplicate_count_nonnegative'),
    sa.CheckConstraint('retry_count >= 0', name='intake_retry_count_nonnegative'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['import_run_id'], ['canada_legacy_import_runs.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['requested_case_id'], ['cases.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('raw_source_reference'),
    sa.UniqueConstraint('source_type', 'source_hash', 'mapping_version', name='uq_intake_source_hash_mapping')
    )
    op.create_index('ix_intake_status_received', 'intake_submissions', ['processing_status', 'received_at'], unique=False)
    op.create_index(op.f('ix_intake_submissions_case_id'), 'intake_submissions', ['case_id'], unique=False)
    op.create_index('uq_intake_external_mapping', 'intake_submissions', ['source_type', 'source_external_id', 'mapping_version'], unique=True, postgresql_where=sa.text('source_external_id IS NOT NULL'), sqlite_where=sa.text('source_external_id IS NOT NULL'))
    op.create_table('legacy_import_entity_links',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('source_type', sa.String(length=40), nullable=False),
    sa.Column('source_record_key', sa.String(length=255), nullable=False),
    sa.Column('canonical_entity_type', sa.String(length=64), nullable=False),
    sa.Column('canonical_entity_id', sa.Uuid(), nullable=False),
    sa.Column('first_import_run_id', sa.Uuid(), nullable=False),
    sa.Column('last_import_run_id', sa.Uuid(), nullable=False),
    sa.Column('employee_order_locked', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['first_import_run_id'], ['canada_legacy_import_runs.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['last_import_run_id'], ['canada_legacy_import_runs.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'source_type', 'source_record_key', 'canonical_entity_type', name='uq_legacy_import_entity_link')
    )
    op.create_index(op.f('ix_legacy_import_entity_links_case_id'), 'legacy_import_entity_links', ['case_id'], unique=False)
    op.create_table('person_biographies',
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('date_of_birth', sa.Date(), nullable=True),
    sa.Column('other_names', sa.String(length=255), nullable=True),
    sa.Column('sex', sa.String(length=32), nullable=True),
    sa.Column('birth_city', sa.String(length=128), nullable=True),
    sa.Column('birth_state_province', sa.String(length=128), nullable=True),
    sa.Column('birth_country_code', sa.String(length=3), nullable=True),
    sa.Column('marital_status', sa.String(length=32), nullable=True),
    sa.Column('occupation_text', sa.String(length=255), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('person_id')
    )
    op.create_table('person_citizenships',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('country_code', sa.String(length=3), nullable=False),
    sa.Column('citizenship_type', sa.String(length=32), nullable=False),
    sa.Column('is_primary', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('person_id', 'country_code', name='uq_person_citizenship')
    )
    op.create_index(op.f('ix_person_citizenships_person_id'), 'person_citizenships', ['person_id'], unique=False)
    op.create_index('uq_person_primary_citizenship', 'person_citizenships', ['person_id'], unique=True, postgresql_where=sa.text('is_primary'), sqlite_where=sa.text('is_primary = 1'))
    op.create_table('person_identifiers',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('country_code', sa.String(length=3), nullable=False),
    sa.Column('identifier_type', sa.String(length=32), nullable=False),
    sa.Column('value', sa.String(length=128), nullable=False),
    sa.Column('issue_date', sa.Date(), nullable=True),
    sa.Column('expiry_date', sa.Date(), nullable=True),
    sa.CheckConstraint('expiry_date IS NULL OR issue_date IS NULL OR expiry_date >= issue_date', name='person_identifier_date_order'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('person_id', 'country_code', 'identifier_type', name='uq_person_identifier')
    )
    op.create_index(op.f('ix_person_identifiers_person_id'), 'person_identifiers', ['person_id'], unique=False)
    op.create_table('preparation_approvals',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('preparation_run_id', sa.Uuid(), nullable=True),
    sa.Column('approval_type', sa.String(length=24), nullable=False),
    sa.Column('decision', sa.String(length=16), nullable=False),
    sa.Column('payload_hash', sa.String(length=64), nullable=False),
    sa.Column('actor', sa.String(length=255), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("(approval_type = 'generation' AND preparation_run_id IS NULL) OR (approval_type = 'package_review' AND preparation_run_id IS NOT NULL)", name='preparation_approval_target_valid'),
    sa.CheckConstraint("approval_type IN ('generation', 'package_review')", name='preparation_approval_type_valid'),
    sa.CheckConstraint("decision IN ('approved', 'rejected')", name='preparation_approval_decision_valid'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['preparation_run_id', 'case_id', 'payload_hash'], ['preparation_runs.id', 'preparation_runs.case_id', 'preparation_runs.payload_hash'], name='fk_preparation_approval_run_identity', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_preparation_approvals_case_created', 'preparation_approvals', ['case_id', 'created_at'], unique=False)
    op.create_index('ix_preparation_approvals_run_created', 'preparation_approvals', ['preparation_run_id', 'created_at'], unique=False)
    op.create_table('preparation_artifacts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('preparation_run_id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('artifact_type', sa.String(length=40), nullable=False),
    sa.Column('display_filename', sa.String(length=255), nullable=False),
    sa.Column('storage_key', sa.Text(), nullable=False),
    sa.Column('mime_type', sa.String(length=128), nullable=False),
    sa.Column('generator', sa.String(length=128), nullable=False),
    sa.Column('generator_version', sa.String(length=128), nullable=False),
    sa.Column('template_identifier', sa.String(length=512), nullable=False),
    sa.Column('template_hash', sa.String(length=64), nullable=False),
    sa.Column('file_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("artifact_type IN ('imm5257', 'imm5707', 'imm5476', 'imm5257_continuation')", name='preparation_artifact_type_valid'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['preparation_run_id', 'case_id'], ['preparation_runs.id', 'preparation_runs.case_id'], name='fk_preparation_artifact_run_case', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('preparation_run_id', 'artifact_type', name='uq_preparation_run_artifact_type')
    )
    op.create_index('ix_preparation_artifacts_case_id', 'preparation_artifacts', ['case_id'], unique=False)
    op.create_table('requirements',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('document_type', sa.String(length=128), nullable=False),
    sa.Column('owner_role', sa.String(length=32), nullable=False),
    sa.Column('owner_person_id', sa.Uuid(), nullable=True),
    sa.Column('requirement_level', sa.String(length=32), nullable=False),
    sa.Column('rule_id', sa.String(length=128), nullable=True),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('is_blocking', sa.Boolean(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('fulfillment_status', sa.Enum('pending', 'fulfilled', 'waived', name='requirement_fulfillment_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('fulfillment_source', sa.Enum('manual', 'automatic_document_evidence', 'waived', name='requirement_fulfillment_source', native_enum=False, create_constraint=True, length=32), nullable=True),
    sa.Column('fulfillment_updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completeness_policy_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('waiver_reason', sa.Text(), nullable=True),
    sa.Column('waived_by', sa.String(length=255), nullable=True),
    sa.Column('waived_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['owner_person_id'], ['persons.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_requirements_case_id', 'requirements', ['case_id'], unique=False)
    op.create_table('activity_records',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('activity_type', sa.String(length=64), nullable=True),
    sa.Column('position', sa.String(length=255), nullable=True),
    sa.Column('organization_name', sa.String(length=255), nullable=True),
    sa.Column('duties', sa.Text(), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('period_status', sa.String(length=24), nullable=False),
    sa.Column('city', sa.String(length=128), nullable=True),
    sa.Column('state_province', sa.String(length=128), nullable=True),
    sa.Column('country_code', sa.String(length=3), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.CheckConstraint("period_status IN ('current', 'completed', 'unknown')", name='activity_period_status_valid'),
    sa.CheckConstraint('end_date IS NULL OR start_date IS NULL OR end_date >= start_date', name='activity_date_order'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'sort_order', name='uq_activity_order')
    )
    op.create_index(op.f('ix_activity_records_application_id'), 'activity_records', ['application_id'], unique=False)
    op.create_index('uq_application_person_current_activity', 'activity_records', ['application_id', 'person_id'], unique=True, postgresql_where=sa.text("period_status = 'current'"), sqlite_where=sa.text("period_status = 'current'"))
    op.create_table('applicant_residences',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('country_code', sa.String(length=3), nullable=False),
    sa.Column('immigration_status_code', sa.String(length=64), nullable=True),
    sa.Column('resident_since', sa.Date(), nullable=True),
    sa.Column('is_current', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_applicant_residences_application_id'), 'applicant_residences', ['application_id'], unique=False)
    op.create_index('uq_application_current_residence', 'applicant_residences', ['application_id'], unique=True, postgresql_where=sa.text('is_current'), sqlite_where=sa.text('is_current = 1'))
    op.create_table('canada_addresses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('context', sa.String(length=32), nullable=False),
    sa.Column('owner_id', sa.Uuid(), nullable=False),
    sa.Column('po_box', sa.String(length=64), nullable=True),
    sa.Column('unit', sa.String(length=64), nullable=True),
    sa.Column('street_number', sa.String(length=64), nullable=True),
    sa.Column('street_name', sa.String(length=255), nullable=True),
    sa.Column('city', sa.String(length=128), nullable=True),
    sa.Column('state_province', sa.String(length=128), nullable=True),
    sa.Column('postal_code', sa.String(length=32), nullable=True),
    sa.Column('country_code', sa.String(length=3), nullable=True),
    sa.Column('unstructured_source_text', sa.Text(), nullable=True),
    sa.Column('review_state', sa.String(length=24), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("context IN ('residential', 'mailing', 'host', 'family_member')", name='canada_address_context_valid'),
    sa.CheckConstraint("review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='canada_address_review_state_valid'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'context', 'owner_id', name='uq_canada_address_owner_context')
    )
    op.create_index(op.f('ix_canada_addresses_application_id'), 'canada_addresses', ['application_id'], unique=False)
    op.create_table('document_classifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.Column('suggested_document_type', sa.String(length=128), nullable=True),
    sa.Column('suggested_person_id', sa.Uuid(), nullable=True),
    sa.Column('extracted_owner_name', sa.String(length=255), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('evidence_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('provider', sa.String(length=64), nullable=False),
    sa.Column('model_version', sa.String(length=128), nullable=True),
    sa.Column('document_hash', sa.String(length=64), nullable=True),
    sa.Column('raw_result_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('status', sa.Enum('pending', 'suggested', 'accepted', 'corrected', 'rejected', 'failed', name='classification_review_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('failure_reason', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reviewed_by', sa.String(length=255), nullable=True),
    sa.Column('corrected_document_type', sa.String(length=128), nullable=True),
    sa.Column('corrected_person_id', sa.Uuid(), nullable=True),
    sa.CheckConstraint('confidence IS NULL OR (confidence >= 0 AND confidence <= 1)', name='classification_confidence_range'),
    sa.ForeignKeyConstraint(['corrected_person_id'], ['persons.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['suggested_person_id'], ['persons.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_classifications_created_at', 'document_classifications', ['created_at'], unique=False)
    op.create_index('ix_document_classifications_document_id', 'document_classifications', ['document_id'], unique=False)
    op.create_table('document_processing_attempts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.Column('idempotency_key', sa.String(length=128), nullable=False),
    sa.Column('retry_of_id', sa.Uuid(), nullable=True),
    sa.Column('trigger', sa.String(length=64), nullable=False),
    sa.Column('stage', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('stage_results_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('error_code', sa.String(length=64), nullable=True),
    sa.Column('error_summary', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("stage IN ('received', 'basic_validation', 'quality_assessment', 'classification', 'matching', 'completeness')", name='document_processing_attempt_stage_valid'),
    sa.CheckConstraint("status IN ('running', 'completed', 'needs_review', 'failed')", name='document_processing_attempt_status_valid'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['retry_of_id', 'document_id'], ['document_processing_attempts.id', 'document_processing_attempts.document_id'], name='fk_document_processing_retry_same_document'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_id', 'idempotency_key', name='uq_document_pipeline_idempotency'),
    sa.UniqueConstraint('id', 'document_id', name='uq_document_processing_attempt_identity')
    )
    op.create_index('ix_document_processing_attempts_document', 'document_processing_attempts', ['document_id', 'created_at'], unique=False)
    op.create_table('document_quality_checks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Enum('checking', 'passed', 'failed', 'manual_review', 'error', name='quality_check_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('checks_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('issues_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('extracted_metadata_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('provider', sa.String(length=64), nullable=False),
    sa.Column('evaluator_version', sa.String(length=128), nullable=True),
    sa.Column('document_hash', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reviewed_by', sa.String(length=255), nullable=True),
    sa.Column('review_decision', sa.Enum('accepted', 'rejected', name='quality_review_decision', native_enum=False, create_constraint=True, length=16), nullable=True),
    sa.Column('review_reason', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_quality_checks_created_at', 'document_quality_checks', ['created_at'], unique=False)
    op.create_index('ix_document_quality_checks_document_id', 'document_quality_checks', ['document_id'], unique=False)
    op.create_table('education_records',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('level', sa.String(length=128), nullable=True),
    sa.Column('institution_name', sa.String(length=255), nullable=True),
    sa.Column('course', sa.String(length=255), nullable=True),
    sa.Column('details', sa.Text(), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('city', sa.String(length=128), nullable=True),
    sa.Column('state_province', sa.String(length=128), nullable=True),
    sa.Column('country_code', sa.String(length=3), nullable=True),
    sa.Column('is_primary', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.CheckConstraint('end_date IS NULL OR start_date IS NULL OR end_date >= start_date', name='education_date_order'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'sort_order', name='uq_education_order')
    )
    op.create_index(op.f('ix_education_records_application_id'), 'education_records', ['application_id'], unique=False)
    op.create_index('uq_application_person_primary_education', 'education_records', ['application_id', 'person_id'], unique=True, postgresql_where=sa.text('is_primary'), sqlite_where=sa.text('is_primary = 1'))
    op.create_table('fact_extraction_candidates',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('conversation_import_id', sa.Uuid(), nullable=True),
    sa.Column('extraction_run_id', sa.Uuid(), nullable=True),
    sa.Column('key', sa.String(length=255), nullable=False),
    sa.Column('value_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('evidence', sa.Text(), nullable=False),
    sa.Column('assertion_type', sa.String(length=16), nullable=False),
    sa.Column('source_message_ids_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('provider', sa.String(length=64), nullable=False),
    sa.Column('model_version', sa.String(length=128), nullable=True),
    sa.Column('status', sa.Enum('proposed', 'conflict', 'accepted', 'corrected', 'rejected', name='fact_candidate_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('conflicting_fact_id', sa.Uuid(), nullable=True),
    sa.Column('authoritative_fact_id', sa.Uuid(), nullable=True),
    sa.Column('corrected_value_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reviewed_by', sa.String(length=255), nullable=True),
    sa.Column('review_reason', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['authoritative_fact_id'], ['facts.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['conflicting_fact_id'], ['facts.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['conversation_import_id'], ['conversation_imports.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['extraction_run_id'], ['fact_extraction_runs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fact_candidates_case_id', 'fact_extraction_candidates', ['case_id'], unique=False)
    op.create_index('ix_fact_candidates_import_id', 'fact_extraction_candidates', ['conversation_import_id'], unique=False)
    op.create_index('ix_fact_candidates_status', 'fact_extraction_candidates', ['status'], unique=False)
    op.create_table('intake_processing_attempts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('submission_id', sa.Uuid(), nullable=False),
    sa.Column('attempt_number', sa.Integer(), nullable=False),
    sa.Column('mapping_version', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failure_code', sa.String(length=64), nullable=True),
    sa.Column('failure_message', sa.Text(), nullable=True),
    sa.Column('failure_detail_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('case_id', sa.Uuid(), nullable=True),
    sa.Column('import_run_id', sa.Uuid(), nullable=True),
    sa.Column('created_case', sa.Integer(), nullable=False),
    sa.Column('matched_existing_case', sa.Integer(), nullable=False),
    sa.Column('issue_count', sa.Integer(), nullable=False),
    sa.CheckConstraint("status IN ('PROCESSING', 'PROCESSED', 'NEEDS_REVIEW', 'FAILED')", name='intake_attempt_status_valid'),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['import_run_id'], ['canada_legacy_import_runs.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['submission_id'], ['intake_submissions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('submission_id', 'attempt_number', name='uq_intake_attempt_number')
    )
    op.create_index(op.f('ix_intake_processing_attempts_submission_id'), 'intake_processing_attempts', ['submission_id'], unique=False)
    op.create_table('official_application_answers',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('question_code', sa.String(length=128), nullable=False),
    sa.Column('answer', sa.String(length=24), nullable=False),
    sa.Column('review_state', sa.String(length=24), nullable=False),
    sa.Column('reviewed_by', sa.String(length=255), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('source_reference', sa.Text(), nullable=True),
    sa.CheckConstraint("answer IN ('yes', 'no', 'not_applicable', 'unknown')", name='official_answer_value_valid'),
    sa.CheckConstraint("review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='official_answer_review_state_valid'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'question_code', name='uq_official_answer_question')
    )
    op.create_index(op.f('ix_official_application_answers_application_id'), 'official_application_answers', ['application_id'], unique=False)
    op.create_table('official_explanations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('section_code', sa.String(length=32), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('review_state', sa.String(length=24), nullable=False),
    sa.Column('reviewed_by', sa.String(length=255), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='official_explanation_review_state_valid'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'section_code', name='uq_official_explanation_section')
    )
    op.create_index(op.f('ix_official_explanations_application_id'), 'official_explanations', ['application_id'], unique=False)
    op.create_table('representative_authorizations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('representative_person_id', sa.Uuid(), nullable=False),
    sa.Column('profile_revision_id', sa.Uuid(), nullable=False),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('cancelled_representative_person_id', sa.Uuid(), nullable=True),
    sa.Column('cancelled_organization_name', sa.String(length=255), nullable=True),
    sa.Column('review_state', sa.String(length=24), nullable=False),
    sa.Column('reviewed_by', sa.String(length=255), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='representative_authorization_review_state_valid'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['cancelled_representative_person_id'], ['persons.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['profile_revision_id'], ['representative_profile_revisions.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['representative_person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id')
    )
    op.create_table('requirement_completeness_evaluations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('requirement_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Enum('complete', 'incomplete', 'not_evaluable', name='requirement_completeness_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('matched_document_ids_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('accepted_document_ids_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('matched_count', sa.Integer(), nullable=False),
    sa.Column('accepted_count', sa.Integer(), nullable=False),
    sa.Column('coverage_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('missing_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('explanation', sa.Text(), nullable=False),
    sa.Column('trigger', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_requirement_completeness_created_at', 'requirement_completeness_evaluations', ['created_at'], unique=False)
    op.create_index('ix_requirement_completeness_requirement_id', 'requirement_completeness_evaluations', ['requirement_id'], unique=False)
    op.create_table('requirement_document_matches',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('requirement_id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('requirement_id', 'document_id', name='uq_requirement_document_match')
    )
    op.create_index('ix_requirement_document_matches_document_id', 'requirement_document_matches', ['document_id'], unique=False)
    op.create_index('ix_requirement_document_matches_requirement_id', 'requirement_document_matches', ['requirement_id'], unique=False)
    op.create_table('requirement_fulfillment_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('requirement_id', sa.Uuid(), nullable=False),
    sa.Column('from_status', sa.String(length=16), nullable=False),
    sa.Column('to_status', sa.String(length=16), nullable=False),
    sa.Column('source', sa.Enum('manual', 'automatic_document_evidence', 'waived', name='fulfillment_event_source', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('actor', sa.String(length=255), nullable=True),
    sa.Column('document_ids_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_requirement_fulfillment_events_requirement_id', 'requirement_fulfillment_events', ['requirement_id'], unique=False)
    op.create_table('residence_history_records',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('country_code', sa.String(length=3), nullable=False),
    sa.Column('status_or_purpose', sa.String(length=128), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('review_state', sa.String(length=24), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.CheckConstraint("review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='residence_history_review_state_valid'),
    sa.CheckConstraint('end_date >= start_date', name='residence_history_date_order'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'sort_order', name='uq_residence_history_order')
    )
    op.create_index(op.f('ix_residence_history_records_application_id'), 'residence_history_records', ['application_id'], unique=False)
    op.create_table('tasks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('case_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.String(length=128), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('priority', sa.String(length=32), nullable=False),
    sa.Column('blocking', sa.Boolean(), nullable=False),
    sa.Column('related_requirement_id', sa.Uuid(), nullable=True),
    sa.Column('related_document_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['related_document_id'], ['documents.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['related_requirement_id'], ['requirements.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tasks_case_id', 'tasks', ['case_id'], unique=False)
    op.create_table('travel_documents',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('document_type', sa.String(length=32), nullable=False),
    sa.Column('number', sa.String(length=128), nullable=False),
    sa.Column('issuing_country_code', sa.String(length=3), nullable=False),
    sa.Column('issue_date', sa.Date(), nullable=True),
    sa.Column('expiry_date', sa.Date(), nullable=True),
    sa.Column('details', sa.Text(), nullable=True),
    sa.Column('is_primary', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.CheckConstraint('expiry_date IS NULL OR issue_date IS NULL OR expiry_date >= issue_date', name='travel_document_date_order'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'sort_order', name='uq_travel_document_order')
    )
    op.create_index(op.f('ix_travel_documents_application_id'), 'travel_documents', ['application_id'], unique=False)
    op.create_index('uq_application_primary_passport', 'travel_documents', ['application_id'], unique=True, postgresql_where=sa.text('is_primary'), sqlite_where=sa.text('is_primary = 1'))
    op.create_table('travel_history_records',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('country_code', sa.String(length=3), nullable=False),
    sa.Column('purpose', sa.String(length=128), nullable=False),
    sa.Column('entry_date', sa.Date(), nullable=False),
    sa.Column('exit_date', sa.Date(), nullable=False),
    sa.Column('review_state', sa.String(length=24), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.CheckConstraint("review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='travel_history_review_state_valid'),
    sa.CheckConstraint('exit_date >= entry_date', name='travel_history_date_order'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'sort_order', name='uq_travel_history_order')
    )
    op.create_index(op.f('ix_travel_history_records_application_id'), 'travel_history_records', ['application_id'], unique=False)
    op.create_table('trip_plans',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('intake_purpose_text', sa.Text(), nullable=True),
    sa.Column('imm5257_purpose_code', sa.String(length=64), nullable=True),
    sa.Column('purpose_review_state', sa.String(length=24), nullable=False),
    sa.Column('arrival_date', sa.Date(), nullable=True),
    sa.Column('departure_date', sa.Date(), nullable=True),
    sa.Column('available_funds_amount', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('available_funds_currency', sa.String(length=3), nullable=True),
    sa.Column('funds_source_reference', sa.Text(), nullable=True),
    sa.CheckConstraint("purpose_review_state IN ('unreviewed', 'confirmed', 'corrected', 'needs_review', 'rejected')", name='trip_purpose_review_state_valid'),
    sa.CheckConstraint('departure_date IS NULL OR arrival_date IS NULL OR departure_date >= arrival_date', name='trip_date_order'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id')
    )
    op.create_table('document_remediation_issues',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.Column('processing_attempt_id', sa.Uuid(), nullable=True),
    sa.Column('problem_type', sa.String(length=64), nullable=False),
    sa.Column('explanation', sa.Text(), nullable=False),
    sa.Column('correction', sa.Text(), nullable=False),
    sa.Column('customer_instructions', sa.Text(), nullable=False),
    sa.Column('language', sa.String(length=16), nullable=False),
    sa.Column('notification_draft', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('resolved_by', sa.String(length=255), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("(status = 'open' AND resolved_by IS NULL AND resolved_at IS NULL) OR (status = 'resolved' AND resolved_by IS NOT NULL AND resolved_at IS NOT NULL)", name='document_remediation_resolution_valid'),
    sa.CheckConstraint("status IN ('open', 'resolved')", name='document_remediation_status_valid'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['processing_attempt_id', 'document_id'], ['document_processing_attempts.id', 'document_processing_attempts.document_id'], name='fk_document_remediation_attempt_same_document'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_remediation_issues_document', 'document_remediation_issues', ['document_id', 'created_at'], unique=False)
    op.create_table('family_relationships',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('applicant_person_id', sa.Uuid(), nullable=False),
    sa.Column('related_person_id', sa.Uuid(), nullable=False),
    sa.Column('relationship_type', sa.String(length=32), nullable=False),
    sa.Column('parent_type', sa.String(length=32), nullable=True),
    sa.Column('guardian_status', sa.String(length=64), nullable=True),
    sa.Column('is_current', sa.Boolean(), nullable=False),
    sa.Column('relationship_start_date', sa.Date(), nullable=True),
    sa.Column('relationship_end_date', sa.Date(), nullable=True),
    sa.Column('previous_relationship_type', sa.String(length=64), nullable=True),
    sa.Column('accompanying_applicant', sa.Boolean(), nullable=True),
    sa.Column('residence_same_as_applicant', sa.Boolean(), nullable=True),
    sa.Column('death_details', sa.Text(), nullable=True),
    sa.Column('address_id', sa.Uuid(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.CheckConstraint("relationship_type IN ('spouse', 'former_spouse', 'parent', 'child')", name='family_relationship_type_valid'),
    sa.CheckConstraint('applicant_person_id <> related_person_id', name='family_relationship_people_differ'),
    sa.CheckConstraint('relationship_end_date IS NULL OR relationship_start_date IS NULL OR relationship_end_date >= relationship_start_date', name='family_relationship_date_order'),
    sa.ForeignKeyConstraint(['address_id'], ['canada_addresses.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['applicant_person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['application_id'], ['canada_applications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['related_person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('address_id'),
    sa.UniqueConstraint('application_id', 'related_person_id', 'relationship_type', name='uq_family_relationship_person_type'),
    sa.UniqueConstraint('application_id', 'relationship_type', 'sort_order', name='uq_family_relationship_order')
    )
    op.create_index(op.f('ix_family_relationships_application_id'), 'family_relationships', ['application_id'], unique=False)
    op.create_index('uq_application_current_spouse', 'family_relationships', ['application_id'], unique=True, postgresql_where=sa.text("relationship_type = 'spouse' AND is_current"), sqlite_where=sa.text("relationship_type = 'spouse' AND is_current = 1"))
    op.create_table('funding_sources',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_plan_id', sa.Uuid(), nullable=False),
    sa.Column('payer_kind', sa.String(length=32), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=True),
    sa.Column('organization_id', sa.Uuid(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('is_primary', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['canada_organizations.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['trip_plan_id'], ['trip_plans.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('trip_plan_id', 'sort_order', name='uq_funding_source_order')
    )
    op.create_index(op.f('ix_funding_sources_trip_plan_id'), 'funding_sources', ['trip_plan_id'], unique=False)
    op.create_table('host_records',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_plan_id', sa.Uuid(), nullable=False),
    sa.Column('host_type', sa.String(length=24), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=True),
    sa.Column('organization_id', sa.Uuid(), nullable=True),
    sa.Column('relationship_to_applicant', sa.String(length=128), nullable=True),
    sa.Column('family_relationship', sa.String(length=128), nullable=True),
    sa.Column('immigration_status_in_canada', sa.String(length=128), nullable=True),
    sa.Column('address_id', sa.Uuid(), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=64), nullable=True),
    sa.Column('is_primary', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.CheckConstraint("(host_type = 'person' AND person_id IS NOT NULL AND organization_id IS NULL) OR (host_type = 'organization' AND organization_id IS NOT NULL AND person_id IS NULL)", name='host_party_xor'),
    sa.CheckConstraint("host_type IN ('person', 'organization')", name='host_type_valid'),
    sa.ForeignKeyConstraint(['address_id'], ['canada_addresses.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['canada_organizations.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['trip_plan_id'], ['trip_plans.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('address_id'),
    sa.UniqueConstraint('trip_plan_id', 'sort_order', name='uq_host_order')
    )
    op.create_index(op.f('ix_host_records_trip_plan_id'), 'host_records', ['trip_plan_id'], unique=False)
    op.create_index('uq_trip_primary_host', 'host_records', ['trip_plan_id'], unique=True, postgresql_where=sa.text('is_primary'), sqlite_where=sa.text('is_primary = 1'))
    # ### end Alembic commands ###



def downgrade() -> None:
    op.drop_table('host_records')
    op.drop_table('funding_sources')
    op.drop_table('family_relationships')
    op.drop_table('document_remediation_issues')
    op.drop_table('trip_plans')
    op.drop_table('travel_history_records')
    op.drop_table('travel_documents')
    op.drop_table('tasks')
    op.drop_table('residence_history_records')
    op.drop_table('requirement_fulfillment_events')
    op.drop_table('requirement_document_matches')
    op.drop_table('requirement_completeness_evaluations')
    op.drop_table('representative_authorizations')
    op.drop_table('official_explanations')
    op.drop_table('official_application_answers')
    op.drop_table('intake_processing_attempts')
    op.drop_table('fact_extraction_candidates')
    op.drop_table('education_records')
    op.drop_table('document_quality_checks')
    op.drop_table('document_processing_attempts')
    op.drop_table('document_classifications')
    op.drop_table('canada_addresses')
    op.drop_table('applicant_residences')
    op.drop_table('activity_records')
    op.drop_table('requirements')
    op.drop_table('preparation_artifacts')
    op.drop_table('preparation_approvals')
    op.drop_table('person_identifiers')
    op.drop_table('person_citizenships')
    op.drop_table('person_biographies')
    op.drop_table('legacy_import_entity_links')
    op.drop_table('intake_submissions')
    op.drop_table('facts')
    op.drop_table('fact_extraction_runs')
    op.drop_table('documents')
    op.drop_table('conversation_messages')
    op.drop_table('contact_points')
    op.drop_table('case_person_roles')
    op.drop_table('canada_import_candidates')
    op.drop_table('canada_applications')
    op.drop_table('workflow_transitions')
    op.drop_table('representative_profile_revisions')
    op.drop_table('preparation_runs')
    op.drop_table('persons')
    op.drop_table('field_provenance_reviews')
    op.drop_table('conversation_imports')
    op.drop_table('canonical_value_revisions')
    op.drop_table('canada_organizations')
    op.drop_table('canada_legacy_import_runs')
    op.drop_table('auth_sessions')
    op.drop_table('auth_security_events')
    op.drop_table('auth_mfa_challenges')
    op.drop_table('application_audit_events')
    op.drop_table('representative_profiles')
    op.drop_table('cases')
    op.drop_table('auth_users')
    op.drop_table('auth_login_throttles')
