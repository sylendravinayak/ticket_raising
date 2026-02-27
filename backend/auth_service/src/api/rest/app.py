from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from src.api.rest.routes.auth import router as auth_router
from src.config.settings import get_settings
from src.data.clients.postgres_client import engine

settings = get_settings()


limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""

    app = FastAPI(
        title="Auth Microservice",
        version="1.0.0",
        description=(
            "JWT authentication service — short-lived access tokens + "
            "DB-backed rotated refresh tokens. No Redis required."
        ),
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )   
    
    app.state.limiter = limiter
    app.include_router(auth_router, prefix="/api/v1")

    return app