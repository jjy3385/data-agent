import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import TablePolicy, UserRole


def test_table_policy_stores_allowed_columns_json_array(admin_session):
    policy = TablePolicy(
        role=UserRole.SUPPLY_RISK_ANALYST,
        schema_name="Sales",
        table_name="SalesOrderHeader",
        allowed_columns=["OrderDate", "TotalDue"],
    )
    admin_session.add(policy)
    admin_session.commit()
    admin_session.refresh(policy)

    assert policy.allowed_columns == ["OrderDate", "TotalDue"]


def test_duplicate_role_schema_table_rejected(admin_session):
    admin_session.add(
        TablePolicy(
            role=UserRole.INVENTORY_VIEWER,
            schema_name="Production",
            table_name="Product",
            allowed_columns=["ProductID"],
        )
    )
    admin_session.commit()

    admin_session.add(
        TablePolicy(
            role=UserRole.INVENTORY_VIEWER,
            schema_name="Production",
            table_name="Product",
            allowed_columns=["Name"],
        )
    )
    with pytest.raises(IntegrityError):
        admin_session.commit()


def test_empty_allowed_columns_array_rejected_by_db_check(admin_session):
    with pytest.raises(IntegrityError):
        admin_session.execute(
            text(
                "INSERT INTO table_policies (role, schema_name, table_name, allowed_columns) "
                "VALUES ('inventory_viewer', 'Production', 'Product', '[]')"
            )
        )
        admin_session.commit()


def test_invalid_json_and_non_array_rejected_by_db_check(admin_session):
    for invalid_value in ["not-json", '{"a": 1}', '"just-a-string"']:
        with pytest.raises(IntegrityError):
            admin_session.execute(
                text(
                    "INSERT INTO table_policies (role, schema_name, table_name, allowed_columns) "
                    "VALUES ('inventory_viewer', 'Production', 'Product', :allowed_columns)"
                ),
                {"allowed_columns": invalid_value},
            )
            admin_session.commit()
        admin_session.rollback()


def test_wildcard_column_rejected_by_orm(admin_session):
    with pytest.raises(ValueError):
        TablePolicy(
            role=UserRole.SUPPLY_RISK_ANALYST,
            schema_name="Sales",
            table_name="SalesOrderHeader",
            allowed_columns=["*"],
        )


def test_blank_column_name_rejected_by_orm(admin_session):
    with pytest.raises(ValueError):
        TablePolicy(
            role=UserRole.SUPPLY_RISK_ANALYST,
            schema_name="Sales",
            table_name="SalesOrderHeader",
            allowed_columns=["OrderDate", "   "],
        )


def test_duplicate_column_name_rejected_by_orm(admin_session):
    with pytest.raises(ValueError):
        TablePolicy(
            role=UserRole.SUPPLY_RISK_ANALYST,
            schema_name="Sales",
            table_name="SalesOrderHeader",
            allowed_columns=["OrderDate", "OrderDate"],
        )
