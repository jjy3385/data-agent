import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.db.schema import prepare_admin_db_schema
from app.db.session import build_admin_db_engine, get_sessionmaker
from app.mcp.lifecycle import mcp_lifespan as _mcp_lifespan
from app.services.schema_collector import build_physical_metadata_catalog

logger = logging.getLogger(__name__)

_MCP_STARTUP_CORRELATION_ID = "startup"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Application startup")

    settings = get_settings()
    engine = build_admin_db_engine(settings.admin_db_path)
    try:
        prepare_admin_db_schema(engine)

        app.state.admin_db_engine = engine
        app.state.admin_db_sessionmaker = get_sessionmaker(engine)

        async with _mcp_lifespan() as mcp_client_manager:
            inspect_schema_result = await mcp_client_manager.inspect_schema(
                correlation_id=_MCP_STARTUP_CORRELATION_ID
            )

            app.state.mcp_client_manager = mcp_client_manager
            app.state.physical_metadata_catalog = build_physical_metadata_catalog(inspect_schema_result)

            yield

        logger.info("Application shutdown")
    finally:
        engine.dispose()
