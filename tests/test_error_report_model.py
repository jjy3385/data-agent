import pytest
from sqlalchemy.exc import IntegrityError

from app.models import AuditLog, AuditStatus, ErrorReport


def _create_audit_log(session, correlation_id: str) -> AuditLog:
    event = AuditLog(correlation_id=correlation_id, workflow_step="acl_check", depth=1, status=AuditStatus.SUCCESS)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def test_correlation_id_required_and_blank_rejected(admin_session):
    with pytest.raises(IntegrityError):
        admin_session.add(ErrorReport(correlation_id="   ", audit_log_id=None))
        admin_session.commit()


def test_error_report_without_audit_log_reference_is_allowed(admin_session):
    report = ErrorReport(correlation_id="corr-standalone", audit_log_id=None)
    admin_session.add(report)
    admin_session.commit()
    admin_session.refresh(report)

    assert report.audit_log_id is None


def test_error_report_with_matching_audit_log_reference_is_allowed(admin_session):
    event = _create_audit_log(admin_session, "corr-match")

    report = ErrorReport(correlation_id="corr-match", audit_log_id=event.id)
    admin_session.add(report)
    admin_session.commit()
    admin_session.refresh(report)

    assert report.audit_log_id == event.id


def test_nonexistent_audit_log_reference_rejected(admin_session):
    admin_session.add(ErrorReport(correlation_id="corr-none", audit_log_id=999_999))
    with pytest.raises(IntegrityError):
        admin_session.commit()


def test_audit_log_reference_with_different_correlation_id_rejected(admin_session):
    event = _create_audit_log(admin_session, "corr-original")

    admin_session.add(ErrorReport(correlation_id="corr-different", audit_log_id=event.id))
    with pytest.raises(IntegrityError):
        admin_session.commit()
