
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.api.middleware.error_handler import register_exception_handlers
from src.api.rest.routes.health import router as health_router
from src.api.rest.routes.tickets import router as ticket_router
from src.data.clients.postgres_client import engine
from src.data.models.postgres import Base  
from src.observability.logging.logger import setup_logging



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title="Ticketing Genie — Ticketing Service",
        version="1.0.0",
        description=(
            "## Authentication\n"
            "1. Login via **Auth Service** `POST /api/v1/auth/login` to get a token.\n"
            "2. Click **Authorize** here and paste: `Bearer <token>`"
        ),
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from src.api.middleware.jwt_middleware import JWTMiddleware
    app.add_middleware(JWTMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(ticket_router)
    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title, version=app.version,
            description=app.description, routes=app.routes,
        )
        schema.setdefault("components", {})["securitySchemes"] = {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        }
        for path_data in schema.get("paths", {}).values():
            for operation in path_data.values():
                if isinstance(operation, dict):
                    operation.setdefault("security", [{"BearerAuth": []}])
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  
    return app