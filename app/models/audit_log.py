from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditStatus(str, Enum):
    SUCCESS = "success"
    PERMISSION_DENIED = "permission_denied"
    CONTRACT_ERROR = "contract_error"
    GUARDRAIL_REJECTED = "guardrail_rejected"
    TIMEOUT = "timeout"
    CONNECTION_CLOSED = "connection_closed"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        UniqueConstraint("id", "correlation_id", name="uq_audit_logs_id_correlation_id"),
        CheckConstraint("length(trim(correlation_id)) > 0", name="ck_audit_logs_correlation_id_not_blank"),
        CheckConstraint("length(trim(workflow_step)) > 0", name="ck_audit_logs_workflow_step_not_blank"),
        CheckConstraint("depth >= 0 AND depth <= 2", name="ck_audit_logs_depth_range"),
        CheckConstraint(
            "status IN ("
            "'success', 'permission_denied', 'contract_error', "
            "'guardrail_rejected', 'timeout', 'connection_closed'"
            ")",
            name="ck_audit_logs_status",
        ),
        CheckConstraint("is_retry IN (0, 1)", name="ck_audit_logs_is_retry_bool"),
        Index("ix_audit_logs_correlation_id", "correlation_id"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    correlation_id: Mapped[str] = mapped_column(String, nullable=False)
    workflow_step: Mapped[str] = mapped_column(String, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AuditStatus] = mapped_column(
        SAEnum(
            AuditStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
            native_enum=False,
            create_constraint=False,
        ),
        nullable=False,
    )
    is_retry: Mapped[bool] = mapped_column(
        Boolean(create_constraint=False), nullable=False, server_default=text("0")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
