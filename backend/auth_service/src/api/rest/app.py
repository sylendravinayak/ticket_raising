
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware.error_handler import register_exception_handlers
from src.api.rest.routes.auth import router as auth_router
from src.config.settings import get_settings
from src.data.clients.postgres_client import engine
from src.data.models.postgres.base import Base
from src.observability.logging.logger import setup_logging
from sqlalchemy import text

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    setup_logging()
    app = FastAPI(
        title="Auth Microservice",
        version="1.0.0",
        description=(
        "Authentication and Authorization microservice for the Ticketing Genie."
        ),
        lifespan=lifespan
    )

    register_exception_handlers(app)
    app.include_router(auth_router, prefix="/api/v1")

    return app
