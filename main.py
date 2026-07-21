from fastapi import FastAPI

from app.api import health
from app.core.config import get_settings
from app.core.lifespan import lifespan

get_settings()

app = FastAPI(lifespan=lifespan)
app.include_router(health.router)
