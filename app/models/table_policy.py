from sqlalchemy import JSON, CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.models.base import Base
from app.models.user import UserRole, user_role_type


class TablePolicy(Base):
    __tablename__ = "table_policies"
    __table_args__ = (
        UniqueConstraint("role", "schema_name", "table_name", name="uq_table_policies_role_schema_table"),
        CheckConstraint(
            "role IN ('supply_risk_analyst', 'inventory_viewer')",
            name="ck_table_policies_role",
        ),
        CheckConstraint("length(trim(schema_name)) > 0", name="ck_table_policies_schema_name_not_blank"),
        CheckConstraint("length(trim(table_name)) > 0", name="ck_table_policies_table_name_not_blank"),
        CheckConstraint(
            "json_valid(allowed_columns)"
            " AND json_type(allowed_columns) = 'array'"
            " AND json_array_length(allowed_columns) >= 1",
            name="ck_table_policies_allowed_columns_nonempty_array",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[UserRole] = mapped_column(user_role_type(), nullable=False)
    schema_name: Mapped[str] = mapped_column(String, nullable=False)
    table_name: Mapped[str] = mapped_column(String, nullable=False)
    allowed_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    @validates("allowed_columns")
    def validate_allowed_columns(self, key: str, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("allowed_columns must be a JSON array")

        seen: set[str] = set()
        for column_name in value:
            if not isinstance(column_name, str):
                raise ValueError("allowed_columns elements must be strings")
            trimmed = column_name.strip()
            if not trimmed:
                raise ValueError("allowed_columns elements must not be blank")
            if trimmed == "*":
                raise ValueError("allowed_columns must not contain the wildcard '*'")
            if column_name in seen:
                raise ValueError(f"allowed_columns contains a duplicate column: {column_name}")
            seen.add(column_name)

        return value
