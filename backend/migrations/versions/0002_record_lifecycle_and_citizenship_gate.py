"""Add retention-safe record lifecycle and explicit citizenship answer.

Revision ID: 0002_record_lifecycle
Revises: 0001_consolidated_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_record_lifecycle"
down_revision = "0001_consolidated_schema"
branch_labels = None
depends_on = None


def _add_lifecycle(table: str, constraint: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.add_column(sa.Column("record_status", sa.String(length=16), nullable=False, server_default="ACTIVE"))
        batch.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("archived_by", sa.String(length=320), nullable=True))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("deleted_by", sa.String(length=320), nullable=True))
        batch.create_check_constraint(
            constraint, "record_status IN ('ACTIVE', 'ARCHIVED', 'DELETED')"
        )


def upgrade() -> None:
    _add_lifecycle("cases", "case_record_status_valid")
    _add_lifecycle("intake_submissions", "intake_record_status_valid")
    with op.batch_alter_table("person_biographies") as batch:
        batch.add_column(sa.Column("has_other_citizenship", sa.Boolean(), nullable=True))


def _drop_lifecycle(table: str, constraint: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.drop_constraint(constraint, type_="check")
        batch.drop_column("deleted_by")
        batch.drop_column("deleted_at")
        batch.drop_column("archived_by")
        batch.drop_column("archived_at")
        batch.drop_column("record_status")


def downgrade() -> None:
    with op.batch_alter_table("person_biographies") as batch:
        batch.drop_column("has_other_citizenship")
    _drop_lifecycle("intake_submissions", "intake_record_status_valid")
    _drop_lifecycle("cases", "case_record_status_valid")
