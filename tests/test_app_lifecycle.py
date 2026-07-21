import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.lifespan import lifespan
from main import app as main_app


def _startup_records(records):
    return [r for r in records if r.name == "app.core.lifespan" and r.message == "Application startup"]


def _shutdown_records(records):
    return [r for r in records if r.name == "app.core.lifespan" and r.message == "Application shutdown"]


def test_lifespan_logs_startup_and_shutdown_exactly_once(caplog):
    test_app = FastAPI(lifespan=lifespan)

    with caplog.at_level(logging.INFO, logger="app.core.lifespan"):
        with TestClient(test_app) as client:
            assert len(_startup_records(caplog.records)) == 1
            assert len(_shutdown_records(caplog.records)) == 0

        assert len(_startup_records(caplog.records)) == 1
        assert len(_shutdown_records(caplog.records)) == 1


def test_main_app_lifespan_logs_startup_and_shutdown_exactly_once(caplog):
    with caplog.at_level(logging.INFO, logger="app.core.lifespan"):
        with TestClient(main_app) as client:
            assert len(_startup_records(caplog.records)) == 1
            assert len(_shutdown_records(caplog.records)) == 0

        assert len(_startup_records(caplog.records)) == 1
        assert len(_shutdown_records(caplog.records)) == 1
