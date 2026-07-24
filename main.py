from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api import health, query
from app.core.config import get_settings
from app.core.lifespan import lifespan

get_settings()

app = FastAPI(lifespan=lifespan)
app.include_router(health.router)
app.include_router(query.router)
app.add_exception_handler(RequestValidationError, query.validation_exception_handler)
