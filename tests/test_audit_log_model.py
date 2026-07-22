import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import AuditLog, AuditStatus


ALLOWED_STATUSES = [
    AuditStatus.SUCCESS,
    AuditStatus.PERMISSION_DENIED,
    AuditStatus.CONTRACT_ERROR,
    AuditStatus.GUARDRAIL_REJECTED,
    AuditStatus.TIMEOUT,
    AuditStatus.CONNECTION_CLOSED,
]


@pytest.mark.parametrize("status", ALLOWED_STATUSES)
def test_allowed_status_values_are_accepted_and_stored_as_lowercase_value(admin_session, status):
    event = AuditLog(correlation_id="corr-1", workflow_step="acl_check", depth=1, status=status)
    admin_session.add(event)
    admin_session.commit()

    stored_status = admin_session.execute(
        text("SELECT status FROM audit_logs WHERE id = :id"), {"id": event.id}
    ).scalar_one()
    assert stored_status == status.value


def test_unknown_status_rejected_by_db_check(admin_session):
    with pytest.raises(IntegrityError):
        admin_session.execute(
            text(
                "INSERT INTO audit_logs (correlation_id, workflow_step, depth, status, is_retry) "
                "VALUES ('corr-1', 'acl_check', 1, 'unknown_status', 0)"
            )
        )
        admin_session.commit()


@pytest.mark.parametrize("depth", [-1, 3])
def test_depth_out_of_range_rejected(admin_session, depth):
    with pytest.raises(IntegrityError):
        admin_session.execute(
            text(
                "INSERT INTO audit_logs (correlation_id, workflow_step, depth, status, is_retry) "
                "VALUES ('corr-1', 'acl_check', :depth, 'success', 0)"
            ),
            {"depth": depth},
        )
        admin_session.commit()


def test_blank_correlation_id_and_workflow_step_rejected(admin_session):
    with pytest.raises(IntegrityError):
        admin_session.add(AuditLog(correlation_id="  ", workflow_step="acl_check", depth=1, status=AuditStatus.SUCCESS))
        admin_session.commit()
    admin_session.rollback()

    with pytest.raises(IntegrityError):
        admin_session.add(AuditLog(correlation_id="corr-1", workflow_step=" ", depth=1, status=AuditStatus.SUCCESS))
        admin_session.commit()


def test_is_retry_defaults_to_false_and_rejects_non_boolean_value(admin_session):
    event = AuditLog(correlation_id="corr-1", workflow_step="acl_check", depth=1, status=AuditStatus.SUCCESS)
    admin_session.add(event)
    admin_session.commit()
    admin_session.refresh(event)
    assert event.is_retry is False

    with pytest.raises(IntegrityError):
        admin_session.execute(
            text(
                "INSERT INTO audit_logs (correlation_id, workflow_step, depth, status, is_retry) "
                "VALUES ('corr-1', 'acl_check', 1, 'success', 2)"
            )
        )
        admin_session.commit()


def test_multiple_events_share_correlation_id_and_order_is_reconstructed_by_id(admin_session):
    correlation_id = "corr-multi"
    first = AuditLog(correlation_id=correlation_id, workflow_step="acl_check", depth=1, status=AuditStatus.SUCCESS)
    admin_session.add(first)
    admin_session.commit()

    second = AuditLog(correlation_id=correlation_id, workflow_step="sql_guardrail", depth=1, status=AuditStatus.GUARDRAIL_REJECTED)
    admin_session.add(second)
    admin_session.commit()

    third = AuditLog(
        correlation_id=correlation_id,
        workflow_step="sql_guardrail",
        depth=1,
        status=AuditStatus.SUCCESS,
        is_retry=True,
    )
    admin_session.add(third)
    admin_session.commit()

    rows = admin_session.execute(
        text(
            "SELECT workflow_step FROM audit_logs "
            "WHERE correlation_id = :correlation_id ORDER BY id"
        ),
        {"correlation_id": correlation_id},
    ).fetchall()

    assert [row[0] for row in rows] == ["acl_check", "sql_guardrail", "sql_guardrail"]


def test_audit_log_id_is_not_reused_after_highest_id_is_deleted(admin_session):
    first = AuditLog(correlation_id="corr-first", workflow_step="acl_check", depth=1, status=AuditStatus.SUCCESS)
    admin_session.add(first)
    admin_session.commit()
    first_id = first.id

    admin_session.delete(first)
    admin_session.commit()

    second = AuditLog(correlation_id="corr-second", workflow_step="acl_check", depth=1, status=AuditStatus.SUCCESS)
    admin_session.add(second)
    admin_session.commit()

    assert second.id > first_id
