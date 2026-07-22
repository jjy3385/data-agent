from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, Enum as SAEnum, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserRole(str, Enum):
    SUPPLY_RISK_ANALYST = "supply_risk_analyst"
    INVENTORY_VIEWER = "inventory_viewer"


def user_role_type() -> SAEnum:
    """users.role/table_policies.role이 공유하는 소문자 value 저장 Enum 타입.

    DB CHECK는 create_constraint=False로 끄고 각 테이블의 명시적 CheckConstraint에 맡긴다.
    """
    return SAEnum(
        UserRole,
        values_callable=lambda enum_cls: [member.value for member in enum_cls],
        validate_strings=True,
        native_enum=False,
        create_constraint=False,
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("slack_user_id", name="uq_users_slack_user_id"),
        CheckConstraint("length(trim(slack_user_id)) > 0", name="ck_users_slack_user_id_not_blank"),
        CheckConstraint("is_active IN (0, 1)", name="ck_users_is_active_bool"),
        CheckConstraint(
            "role IN ('supply_risk_analyst', 'inventory_viewer')",
            name="ck_users_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slack_user_id: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean(create_constraint=False), nullable=False, server_default=text("1")
    )
    role: Mapped[UserRole] = mapped_column(user_role_type(), nullable=False)
