"""add document pipeline, remediation and final-review approvals

Revision ID: 0018_doc_pipeline_final_review
Revises: 0017_dynamic_case_foundation
Create Date: 2026-10-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0018_doc_pipeline_final_review"
down_revision: str | None = "0017_dynamic_case_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if all(inspector.has_table(name) for name in (
        "document_processing_attempts",
        "document_remediation_issues",
        "preparation_approvals",
    )):
        # Supports test/bootstrap databases created from current ORM metadata
        # and then stamped at an older revision.
        return
    op.create_table(
        "document_processing_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("retry_of_id", sa.Uuid(), nullable=True),
        sa.Column("trigger", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("stage_results_json", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_summary", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'needs_review', 'failed')",
            name="document_processing_attempt_status_valid",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["retry_of_id"], ["document_processing_attempts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "idempotency_key", name="uq_document_pipeline_idempotency"),
    )
    op.create_index(
        "ix_document_processing_attempts_document", "document_processing_attempts",
        ["document_id", "created_at"], unique=False,
    )
    op.create_table(
        "document_remediation_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("processing_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("problem_type", sa.String(length=64), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("correction", sa.Text(), nullable=False),
        sa.Column("customer_instructions", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("notification_draft", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("resolved_by", sa.String(length=255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="document_remediation_status_valid"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_attempt_id"], ["document_processing_attempts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_remediation_issues_document", "document_remediation_issues",
        ["document_id", "created_at"], unique=False,
    )
    op.create_table(
        "preparation_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("preparation_run_id", sa.Uuid(), nullable=True),
        sa.Column("approval_type", sa.String(length=24), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("approval_type IN ('generation', 'package_review')", name="preparation_approval_type_valid"),
        sa.CheckConstraint("decision IN ('approved', 'rejected')", name="preparation_approval_decision_valid"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["preparation_run_id"], ["preparation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_preparation_approvals_case_created", "preparation_approvals", ["case_id", "created_at"])
    op.create_index("ix_preparation_approvals_run_created", "preparation_approvals", ["preparation_run_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_preparation_approvals_run_created", table_name="preparation_approvals")
    op.drop_index("ix_preparation_approvals_case_created", table_name="preparation_approvals")
    op.drop_table("preparation_approvals")
    op.drop_index("ix_document_remediation_issues_document", table_name="document_remediation_issues")
    op.drop_table("document_remediation_issues")
    op.drop_index("ix_document_processing_attempts_document", table_name="document_processing_attempts")
    op.drop_table("document_processing_attempts")
