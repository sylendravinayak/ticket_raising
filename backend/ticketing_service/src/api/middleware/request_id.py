import uuid
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())

        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger.info("request_started", path=request.url.path)

        response = await call_next(request)

        logger.info(
            "request_completed",
            status_code=response.status_code,
        )

        response.headers["X-Request-ID"] = request_id
        return response