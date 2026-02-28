from collections.abc import AsyncGenerator
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from src.data.clients.postgres_client import engine
from auth_service.src.config.settings import get_settings
from auth_service.src.data.models.postgres.base import Base
from src.api.middleware import register_middlewares
from src.api.middleware.logging import setup_logging
from src.api.rest.routes.health import router as health_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
def create_app() -> FastAPI:
    setup_logging(debug=True)

    app = FastAPI(
        title="Ticket Genie",
        version="2.0",
        lifespan=lifespan
    )
    app.include_router(health_router)
    register_middlewares(app)

    return app