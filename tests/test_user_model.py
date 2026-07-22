import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import User, UserRole


@pytest.mark.parametrize("role", [UserRole.SUPPLY_RISK_ANALYST, UserRole.INVENTORY_VIEWER])
def test_allowed_roles_are_accepted_and_stored_as_lowercase_value(admin_session, role):
    user = User(slack_user_id=f"U-{role.value}", role=role)
    admin_session.add(user)
    admin_session.commit()

    stored_role = admin_session.execute(
        text("SELECT role FROM users WHERE id = :id"), {"id": user.id}
    ).scalar_one()
    assert stored_role == role.value


def test_unknown_role_rejected_by_db_check(admin_session):
    with pytest.raises(IntegrityError):
        admin_session.execute(
            text(
                "INSERT INTO users (slack_user_id, is_active, role) "
                "VALUES ('U-unknown', 1, 'admin')"
            )
        )
        admin_session.commit()


def test_duplicate_slack_user_id_rejected(admin_session):
    admin_session.add(User(slack_user_id="U-dup", role=UserRole.INVENTORY_VIEWER))
    admin_session.commit()

    admin_session.add(User(slack_user_id="U-dup", role=UserRole.SUPPLY_RISK_ANALYST))
    with pytest.raises(IntegrityError):
        admin_session.commit()


def test_blank_slack_user_id_rejected(admin_session):
    admin_session.add(User(slack_user_id="   ", role=UserRole.INVENTORY_VIEWER))
    with pytest.raises(IntegrityError):
        admin_session.commit()


def test_is_active_defaults_to_true_and_rejects_non_boolean_value(admin_session):
    user = User(slack_user_id="U-active", role=UserRole.INVENTORY_VIEWER)
    admin_session.add(user)
    admin_session.commit()
    admin_session.refresh(user)
    assert user.is_active is True

    with pytest.raises(IntegrityError):
        admin_session.execute(
            text(
                "INSERT INTO users (slack_user_id, is_active, role) "
                "VALUES ('U-bad-bool', 2, 'inventory_viewer')"
            )
        )
        admin_session.commit()
