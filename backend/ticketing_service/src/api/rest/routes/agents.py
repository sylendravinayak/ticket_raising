"""Agent management endpoints for syncing with Auth Service."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.services.agent_service import AgentService
from src.schemas.agent_schema import AgentProfileResponse, AgentProfileSyncRequest

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
security = HTTPBearer()


async def verify_internal_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Verify that the request is from an authorized internal service.
    For now, this is a simple bearer token check.
    In production, implement JWT validation or mTLS.
    """
    # TODO: Implement proper inter-service authentication
    # For now, accept any bearer token (insecure for demo purposes)
    if not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return credentials.credentials


@router.post(
    "/sync",
    response_model=AgentProfileResponse,
    summary="Sync agent profile from Auth Service",
    status_code=status.HTTP_200_OK,
)
async def sync_agent_profile(
    payload: AgentProfileSyncRequest,
    token: str = Depends(verify_internal_token),
) -> AgentProfileResponse:
    """
    Receive and sync agent profile updates from Auth Service.
    Called when:
    - An agent is created
    - An agent's details are updated
    - An agent's availability changes

    This endpoint should only be accessible from Auth Service (internal communication).
    """
    service = AgentService()
    profile = await service.sync_agent_profile(payload)
    return AgentProfileResponse.model_validate(profile)


@router.patch(
    "/{user_id}/availability",
    response_model=AgentProfileResponse,
    summary="Update agent availability",
    status_code=status.HTTP_200_OK,
)
async def update_agent_availability(
    user_id: str,
    is_available: bool,
    token: str = Depends(verify_internal_token),
) -> AgentProfileResponse:
    """
    Update an agent's availability status (online/offline).
    Called when agents go online/offline.
    """
    service = AgentService()
    profile = await service.update_agent_availability(user_id, is_available)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent profile not found for user_id: {user_id}",
        )
    return AgentProfileResponse.model_validate(profile)
