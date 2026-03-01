import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict
from src.constants.enum import EventType


class TicketEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    event_type: EventType
    metadata_: Optional[dict[str, Any]] = None
    actor_id: Optional[uuid.UUID]
    actor_role: Optional[str]
    created_at: datetime