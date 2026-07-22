from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ErrorReport(Base):
    __tablename__ = "error_reports"
    __table_args__ = (
        CheckConstraint("length(trim(correlation_id)) > 0", name="ck_error_reports_correlation_id_not_blank"),
        ForeignKeyConstraint(
            ["audit_log_id", "correlation_id"],
            ["audit_logs.id", "audit_logs.correlation_id"],
            name="fk_error_reports_audit_log_correlation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    correlation_id: Mapped[str] = mapped_column(String, nullable=False)
    audit_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
