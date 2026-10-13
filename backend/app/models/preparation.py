from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .core import utcnow


class PreparationRun(Base):
    __tablename__ = "preparation_runs"
    __table_args__ = (
        CheckConstraint("status IN ('running', 'succeeded', 'failed')", name="preparation_run_status_valid"),
        UniqueConstraint("id", "case_id", name="uq_preparation_run_case_identity"),
        UniqueConstraint("id", "case_id", "payload_hash", name="uq_preparation_run_identity"),
        Index("ix_preparation_runs_case_created", "case_id", "created_at"),
        Index(
            "uq_preparation_running_case", "case_id", unique=True,
            postgresql_where=text("status = 'running'"),
            sqlite_where=text("status = 'running'"),
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    initiated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    preparation_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(32), nullable=False)
    generator_version: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_summary: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    artifacts: Mapped[list[PreparationArtifact]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class PreparationArtifact(Base):
    __tablename__ = "preparation_artifacts"
    __table_args__ = (
        UniqueConstraint("preparation_run_id", "artifact_type", name="uq_preparation_run_artifact_type"),
        ForeignKeyConstraint(
            ["preparation_run_id", "case_id"],
            ["preparation_runs.id", "preparation_runs.case_id"],
            name="fk_preparation_artifact_run_case",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "artifact_type IN ('imm5257', 'imm5707', 'imm5476', 'imm5257_continuation')",
            name="preparation_artifact_type_valid",
        ),
        Index("ix_preparation_artifacts_case_id", "case_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    preparation_run_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    display_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    generator: Mapped[str] = mapped_column(String(128), nullable=False)
    generator_version: Mapped[str] = mapped_column(String(128), nullable=False)
    template_identifier: Mapped[str] = mapped_column(String(512), nullable=False)
    template_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    run: Mapped[PreparationRun] = relationship(back_populates="artifacts")


class PreparationApproval(Base):
    """Immutable approval ledger for generation and generated-package review."""

    __tablename__ = "preparation_approvals"
    __table_args__ = (
        CheckConstraint(
            "approval_type IN ('generation', 'package_review')",
            name="preparation_approval_type_valid",
        ),
        CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="preparation_approval_decision_valid",
        ),
        CheckConstraint(
            "(approval_type = 'generation' AND preparation_run_id IS NULL) OR "
            "(approval_type = 'package_review' AND preparation_run_id IS NOT NULL)",
            name="preparation_approval_target_valid",
        ),
        ForeignKeyConstraint(
            ["preparation_run_id", "case_id", "payload_hash"],
            ["preparation_runs.id", "preparation_runs.case_id", "preparation_runs.payload_hash"],
            name="fk_preparation_approval_run_identity",
            ondelete="CASCADE",
        ),
        Index("ix_preparation_approvals_case_created", "case_id", "created_at"),
        Index("ix_preparation_approvals_run_created", "preparation_run_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    preparation_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    approval_type: Mapped[str] = mapped_column(String(24), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
