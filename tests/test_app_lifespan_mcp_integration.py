from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.mcp.client_manager import MCPStartupError
from app.services.schema_collector import PhysicalMetadataCatalog
from main import app as main_app


def test_startup_populates_mcp_client_manager_and_catalog(admin_db_path):
    with TestClient(main_app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        assert main_app.state.mcp_client_manager is not None
        assert isinstance(main_app.state.physical_metadata_catalog, PhysicalMetadataCatalog)
        assert main_app.state.physical_metadata_catalog.schemas[0].schema_name == "Production"


def test_mcp_startup_failure_is_fail_closed_and_disposes_admin_db_engine(admin_db_path, monkeypatch):
    @asynccontextmanager
    async def failing_mcp_lifespan():
        raise MCPStartupError("simulated startup failure", reason="startup_failed")
        yield  # pragma: no cover - unreachable, keeps this an async generator

    monkeypatch.setattr("app.core.lifespan._mcp_lifespan", failing_mcp_lifespan)

    disposed_engines = []
    original_dispose = Engine.dispose

    def _tracking_dispose(self, *args, **kwargs):
        disposed_engines.append(self)
        return original_dispose(self, *args, **kwargs)

    monkeypatch.setattr(Engine, "dispose", _tracking_dispose)

    with pytest.raises(MCPStartupError):
        with TestClient(main_app):
            pass

    assert main_app.state.admin_db_engine is not None
    assert disposed_engines == [main_app.state.admin_db_engine]
