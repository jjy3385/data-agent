import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.db.schema import prepare_admin_db_schema
from app.db.session import build_admin_db_engine, get_sessionmaker
from app.mcp.lifecycle import mcp_lifespan as _mcp_lifespan
from app.services import metadata_service
from app.services.llm_client import OpenAICompatibleLLMClient
from app.services.schema_collector import build_physical_metadata_catalog

logger = logging.getLogger(__name__)

_MCP_STARTUP_CORRELATION_ID = "startup"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Application startup")

    settings = get_settings()
    engine = build_admin_db_engine(settings.admin_db_path)
    # Wrapper 생성 자체는 설정 검증이나 네트워크 호출을 하지 않으므로 LLM 설정이 없어도
    # Startup을 막지 않는다(요청 시점에 llm_unavailable로 나타난다).
    llm_client = OpenAICompatibleLLMClient()
    try:
        prepare_admin_db_schema(engine)

        app.state.admin_db_engine = engine
        app.state.admin_db_sessionmaker = get_sessionmaker(engine)
        app.state.llm_client = llm_client

        async with _mcp_lifespan() as mcp_client_manager:
            inspect_schema_result = await mcp_client_manager.inspect_schema(
                correlation_id=_MCP_STARTUP_CORRELATION_ID
            )

            physical_metadata_catalog = build_physical_metadata_catalog(inspect_schema_result)
            # Business Metadata가 가정하는 물리 매핑이 실제 Catalog와 어긋나면 여기서 예외가
            # 전파되어 ASGI Startup을 완료시키지 않는다(Fail Closed).
            metadata_service.validate_physical_mapping(physical_metadata_catalog)

            app.state.mcp_client_manager = mcp_client_manager
            app.state.physical_metadata_catalog = physical_metadata_catalog

            yield

        logger.info("Application shutdown")
    finally:
        try:
            await llm_client.aclose()
        finally:
            engine.dispose()
