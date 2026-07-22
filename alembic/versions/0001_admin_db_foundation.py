"""Admin DB foundation: users, table_policies, audit_logs, error_reports

Revision ID: 0001
Revises:
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slack_user_id", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(create_constraint=False), nullable=False, server_default=sa.text("1")),
        sa.Column("role", sa.String(), nullable=False),
        sa.UniqueConstraint("slack_user_id", name="uq_users_slack_user_id"),
        sa.CheckConstraint("length(trim(slack_user_id)) > 0", name="ck_users_slack_user_id_not_blank"),
        sa.CheckConstraint("is_active IN (0, 1)", name="ck_users_is_active_bool"),
        sa.CheckConstraint(
            "role IN ('supply_risk_analyst', 'inventory_viewer')",
            name="ck_users_role",
        ),
    )

    op.create_table(
        "table_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("schema_name", sa.String(), nullable=False),
        sa.Column("table_name", sa.String(), nullable=False),
        sa.Column("allowed_columns", sa.JSON(), nullable=False),
        sa.UniqueConstraint("role", "schema_name", "table_name", name="uq_table_policies_role_schema_table"),
        sa.CheckConstraint(
            "role IN ('supply_risk_analyst', 'inventory_viewer')",
            name="ck_table_policies_role",
        ),
        sa.CheckConstraint("length(trim(schema_name)) > 0", name="ck_table_policies_schema_name_not_blank"),
        sa.CheckConstraint("length(trim(table_name)) > 0", name="ck_table_policies_table_name_not_blank"),
        sa.CheckConstraint(
            "json_valid(allowed_columns)"
            " AND json_type(allowed_columns) = 'array'"
            " AND json_array_length(allowed_columns) >= 1",
            name="ck_table_policies_allowed_columns_nonempty_array",
        ),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("correlation_id", sa.String(), nullable=False),
        sa.Column("workflow_step", sa.String(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("is_retry", sa.Boolean(create_constraint=False), nullable=False, server_default=sa.text("0")),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("id", "correlation_id", name="uq_audit_logs_id_correlation_id"),
        sa.CheckConstraint("length(trim(correlation_id)) > 0", name="ck_audit_logs_correlation_id_not_blank"),
        sa.CheckConstraint("length(trim(workflow_step)) > 0", name="ck_audit_logs_workflow_step_not_blank"),
        sa.CheckConstraint("depth >= 0 AND depth <= 2", name="ck_audit_logs_depth_range"),
        sa.CheckConstraint(
            "status IN ("
            "'success', 'permission_denied', 'contract_error', "
            "'guardrail_rejected', 'timeout', 'connection_closed'"
            ")",
            name="ck_audit_logs_status",
        ),
        sa.CheckConstraint("is_retry IN (0, 1)", name="ck_audit_logs_is_retry_bool"),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_audit_logs_correlation_id", "audit_logs", ["correlation_id"])

    op.create_table(
        "error_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("correlation_id", sa.String(), nullable=False),
        sa.Column("audit_log_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("length(trim(correlation_id)) > 0", name="ck_error_reports_correlation_id_not_blank"),
        sa.ForeignKeyConstraint(
            ["audit_log_id", "correlation_id"],
            ["audit_logs.id", "audit_logs.correlation_id"],
            name="fk_error_reports_audit_log_correlation",
        ),
    )


def downgrade() -> None:
    op.drop_table("error_reports")
    op.drop_index("ix_audit_logs_correlation_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("table_policies")
    op.drop_table("users")
