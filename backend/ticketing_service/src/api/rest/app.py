from collections.abc import AsyncGenerator

from src.data.models.postgres.base import Base
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager

from src.api.middleware import register_middlewares
from src.api.rest.routes.health import router as health_router
from src.data.clients.postgres_client import engine
from src.observability.logging.logger import setup_logging
from src.api.middleware.cors import setup_cors
from src.api.middleware.error_handler import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title="Ticket Genie",
        version="2.0",
        lifespan=lifespan
    )
    register_exception_handlers(app)
    setup_cors(app)

    app.include_router(health_router)
    return app
