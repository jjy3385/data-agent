import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.db.schema import prepare_admin_db_schema
from app.db.session import build_admin_db_engine, get_sessionmaker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Application startup")

    settings = get_settings()
    engine = build_admin_db_engine(settings.admin_db_path)
    try:
        prepare_admin_db_schema(engine)
    except Exception:
        engine.dispose()
        raise

    app.state.admin_db_engine = engine
    app.state.admin_db_sessionmaker = get_sessionmaker(engine)

    try:
        yield
    finally:
        engine.dispose()
        logger.info("Application shutdown")
