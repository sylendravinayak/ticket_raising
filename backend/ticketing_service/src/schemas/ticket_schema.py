"""
Pydantic v2 schemas for the Ticket creation pipeline.
All request/response models live here.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.constants.enum import (
    Environment,
    EventType,
    NotificationChannel,
    NotificationStatus,
    Priority,
    Severity,
    TicketSource,
    TicketStatus,
)


# ─────────────────────────────────────────────
# Attachment
# ─────────────────────────────────────────────

class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attachment_id: int
    ticket_id: int
    file_name: str
    file_url: str
    uploaded_by_user_id: int
    uploaded_at: datetime


# ─────────────────────────────────────────────
# Ticket Event
# ─────────────────────────────────────────────

class TicketEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: int
    ticket_id: int
    triggered_by_user_id: Optional[int] = None
    event_type: EventType
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    comment_id: Optional[int] = None
    created_at: datetime


# ─────────────────────────────────────────────
# Comment
# ─────────────────────────────────────────────

class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    comment_id: int
    ticket_id: int
    user_id: int
    message: str
    is_internal: bool
    is_mandatory_note: bool
    created_at: datetime


# ─────────────────────────────────────────────
# Ticket — CREATE
# ─────────────────────────────────────────────

class TicketCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10)
    product: str = Field(..., min_length=1, max_length=100)
    environment: Environment
    source: TicketSource = TicketSource.UI
    area_of_concern: Optional[str] = Field(default=None, max_length=255)
    attachments: list[str] = Field(default_factory=list)  # list of file URLs


# ─────────────────────────────────────────────
# Ticket — STATUS TRANSITION
# ─────────────────────────────────────────────

class TicketStatusUpdateRequest(BaseModel):
    new_status: TicketStatus
    comment: Optional[str] = Field(default=None, max_length=2000)


# ─────────────────────────────────────────────
# Ticket — ASSIGN
# ─────────────────────────────────────────────

class TicketAssignRequest(BaseModel):
    assignee_id: int = Field(..., gt=0)


# ─────────────────────────────────────────────
# Ticket — RESPONSE
# ─────────────────────────────────────────────

class TicketBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: int
    ticket_number: str
    title: str
    status: TicketStatus
    severity: Severity
    priority: Priority
    environment: Environment
    product: str
    area_of_concern: Optional[str] = None
    source: TicketSource
    customer_id: int
    assignee_id: Optional[int] = None
    sla_id: Optional[int] = None
    customer_tier_id: Optional[int] = None
    is_breached: bool
    is_escalated: bool
    response_due_at: Optional[datetime] = None
    resolution_due_at: Optional[datetime] = None
    hold_started_at: Optional[datetime] = None
    total_hold_minutes: int
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TicketDetailResponse(TicketBriefResponse):
    description: str
    attachments: list[AttachmentResponse] = []
    comments: list[CommentResponse] = []
    events: list[TicketEventResponse] = []


# ─────────────────────────────────────────────
# Ticket — LIST FILTERS
# ─────────────────────────────────────────────

class TicketListFilters(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[Priority] = None
    severity: Optional[Severity] = None
    is_breached: Optional[bool] = None
    is_escalated: Optional[bool] = None
    assignee_id: Optional[int] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ─────────────────────────────────────────────
# Notification Log
# ─────────────────────────────────────────────

class NotificationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    ticket_id: int
    recipient_user_id: int
    channel: NotificationChannel
    event_type: str
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    created_at: datetime