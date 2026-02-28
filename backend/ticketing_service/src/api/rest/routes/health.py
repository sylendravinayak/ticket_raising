import structlog
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])
logger = structlog.get_logger(__name__)

@router.get("/")
async def health_check():
    logger.info("health_check_called")
    return {"status": "ok"}