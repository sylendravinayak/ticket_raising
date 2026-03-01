import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from src.constants.enum import (
    TicketStatus, Priority, Severity, Channel, CustomerTier
)


class AttachmentSchema(BaseModel):
    url: str
    name: str


# ── Create ────────────────────────────────────────────────
class TicketCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10)
    product: Optional[str] = None
    area_of_concern: Optional[str] = None
    attachments: list[AttachmentSchema] = Field(default_factory=list)
    preferred_contact: Optional[str] = None

    # Injected server-side (not from user input)
    channel: Channel = Channel.UI


class EmailIngestRequest(BaseModel):
    from_email: str = Field(..., alias="from")
    subject: str
    body: str
    thread_id: str
    message_id: str
    attachments: list[AttachmentSchema] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


# ── Update ────────────────────────────────────────────────
class TicketUpdateRequest(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[Priority] = None
    severity: Optional[Severity] = None
    assigned_agent_id: Optional[uuid.UUID] = None
    override_justification: Optional[str] = Field(None, min_length=10)


class TicketAssignRequest(BaseModel):
    agent_id: uuid.UUID


class TicketReopenRequest(BaseModel):
    reason: Optional[str] = None


# ── Comment ───────────────────────────────────────────────
class CommentCreateRequest(BaseModel):
    body: str = Field(..., min_length=1)
    is_internal: bool = False
    attachments: list[AttachmentSchema] = Field(default_factory=list)


# ── Responses ─────────────────────────────────────────────
class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    body: str
    author_id: uuid.UUID
    author_role: str
    is_internal: bool
    attachments: list[AttachmentSchema]
    created_at: datetime


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    product: Optional[str]
    area_of_concern: Optional[str]
    status: TicketStatus
    priority: Priority
    severity: Severity
    channel: Channel
    customer_id: uuid.UUID
    assigned_agent_id: Optional[uuid.UUID]
    sla_id: Optional[uuid.UUID]
    response_due_at: Optional[datetime]
    resolution_due_at: Optional[datetime]
    sla_breached: bool
    is_escalated: bool
    email_thread_id: Optional[str]
    attachments: list[AttachmentSchema]
    created_at: datetime
    updated_at: datetime


class TicketDetailResponse(TicketResponse):
    comments: list[CommentResponse] = []