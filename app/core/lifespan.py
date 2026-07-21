import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Application startup")
    try:
        yield
    finally:
        logger.info("Application shutdown")
