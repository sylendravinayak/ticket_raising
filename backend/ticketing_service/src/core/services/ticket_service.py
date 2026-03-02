"""
Ticket Service — enterprise workflow.

Lifecycle:
  NEW (auto) → ACKNOWLEDGED (auto) → OPEN → IN_PROGRESS → ON_HOLD ↔ IN_PROGRESS
  IN_PROGRESS → RESOLVED → CLOSED → OPEN (reopen)

Response SLA : NEW → ACKNOWLEDGED → OPEN → stops at IN_PROGRESS
Resolution SLA: starts IN_PROGRESS, pauses ON_HOLD, stops RESOLVED, restarts on reopen
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.constants.enum import (
    EventType, NotificationChannel, NotificationStatus,
    Priority, Severity, TicketStatus, UserRole,
)
from src.core.exceptions.base import (
    InsufficientPermissionsError,
    InvalidStatusTransitionError,
    TicketNotFoundError,
)
from src.core.services.classification_service import ClassificationService
from src.core.services.sla_service import SLAService
from src.data.clients.auth_client import AuthServiceClient, UserDTO
from src.data.models.postgres.notification_log import NotificationLog
from src.data.models.postgres.ticket import Ticket
from src.data.models.postgres.ticket_attachment import TicketAttachment
from src.data.models.postgres.ticket_event import TicketEvent
from src.data.repositories.agent_repository import AgentRepository
from src.data.repositories.keyword_repository import KeywordRepository
from src.data.repositories.sla_repository import SLARepository
from src.data.repositories.ticket_repository import TicketRepository
from src.schemas.ticket_schema import (
    TicketAssignRequest,
    TicketCreateRequest,
    TicketListFilters,
    TicketStatusUpdateRequest,
)

logger = logging.getLogger(__name__)

# ── Strict transition matrix ──────────────────────────────────────────────────
ALLOWED_TRANSITIONS: dict[TicketStatus, list[TicketStatus]] = {
    TicketStatus.NEW:          [TicketStatus.ACKNOWLEDGED],
    TicketStatus.ACKNOWLEDGED: [TicketStatus.OPEN],
    TicketStatus.OPEN:         [TicketStatus.IN_PROGRESS],
    TicketStatus.IN_PROGRESS:  [TicketStatus.ON_HOLD, TicketStatus.RESOLVED],
    TicketStatus.ON_HOLD:      [TicketStatus.IN_PROGRESS],
    TicketStatus.RESOLVED:     [TicketStatus.CLOSED],
    TicketStatus.CLOSED:       [TicketStatus.OPEN],   # reopen
}

SYSTEM = "SYSTEM"


class TicketService:
    def __init__(self, db: AsyncSession, auth_client: AuthServiceClient) -> None:
        self.db = db
        self._auth = auth_client
        self._ticket_repo = TicketRepository(db)
        self._sla_repo = SLARepository(db)
        self._keyword_repo = KeywordRepository(db)
        self._agent_repo = AgentRepository(db)

        self._classifier = ClassificationService(self._keyword_repo)
        self._sla_svc = SLAService(self._sla_repo)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get_or_404(self, ticket_id: int) -> Ticket:
        ticket = await self._ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found.")
        return ticket

    async def _record_transition(
    self,
    ticket: Ticket,
    from_status: TicketStatus | None,
    to_status: TicketStatus,
    changed_by: str,                # UUID string or "SYSTEM"
    reason: str | None = None,
) -> None:
        """
        Write a STATUS_CHANGED TicketEvent row.
        This IS the timeline — filter ticket_events by event_type=STATUS_CHANGED
        to reconstruct the full transition history.
        """
        await self._ticket_repo.add_event(TicketEvent(
            ticket_id=ticket.ticket_id,
            # triggered_by_user_id is None for SYSTEM events
            triggered_by_user_id=changed_by if changed_by != "SYSTEM" else None,
            event_type=EventType.STATUS_CHANGED,
            field_name="status",
            from_status=from_status.value if from_status else None,
            old_value=from_status.value if from_status else None,
            new_value=to_status.value,
            reason=reason,
        ))

    # ── CREATE ────────────────────────────────────────────────────────────────

    async def create_ticket(
        self,
        payload: TicketCreateRequest,
        current_user_id: str,
    ) -> Ticket:
        """
        Pipeline:
          1. Classify → severity/priority
          2. SLA config lookup
          3. Persist ticket at status=NEW + start response SLA
          4. Log NEW creation in timeline
          5. Auto-transition → ACKNOWLEDGED (SYSTEM)
          6. Send acknowledgement notification
        """
        now = datetime.now(timezone.utc)
        settings = get_settings()

        # 1. Fetch user (for tier lookup)
        customer: UserDTO = await self._auth.get_user(current_user_id)

        # 2. Classify
        classification = await self._classifier.classify(payload.title, payload.description)
        severity: Severity = classification.severity
        priority: Priority = classification.priority

        # 3. SLA config
        sla_config = await self._sla_svc.resolve_config(
            customer_tier_id=customer.customer_tier_id,
            severity=severity,
            priority=priority,
        )

        # 4. Build ticket number
        ticket_number = await self._ticket_repo.next_ticket_number()

        # 5. Persist ticket at NEW
        ticket = Ticket(
            ticket_number=ticket_number,
            title=payload.title,
            description=payload.description,
            product=payload.product,
            environment=payload.environment,
            source=payload.source,
            area_of_concern=payload.area_of_concern,
            severity=severity,
            priority=priority,
            status=TicketStatus.NEW,
            customer_id=current_user_id,
            customer_tier_id=customer.customer_tier_id,
            response_sla_deadline_minutes=sla_config.response_deadline_minutes,
            resolution_sla_deadline_minutes=sla_config.resolution_deadline_minutes,
            escalation_level=0,
            auto_closed=False,
        )

        # Start response SLA immediately
        self._sla_svc.start_response_sla(ticket, now)

        ticket = await self._ticket_repo.create(ticket)

        # 6. Timeline: creation (from_status=None → NEW)
        await self._record_transition(
            ticket, from_status=None, to_status=TicketStatus.NEW,
            changed_by=current_user_id, reason="Ticket created",
        )

        # 7. Attachment stubs
        for url in payload.attachments:
            await self._ticket_repo.add_attachment(TicketAttachment(
                ticket_id=ticket.ticket_id,
                file_name=url.split("/")[-1],
                file_url=url,
                uploaded_by_user_id=current_user_id,
            ))

        # 8. Auto-transition → ACKNOWLEDGED (SYSTEM)
        ticket.status = TicketStatus.ACKNOWLEDGED
        ticket = await self._ticket_repo.save(ticket)
        await self._record_transition(
            ticket,
            from_status=TicketStatus.NEW,
            to_status=TicketStatus.ACKNOWLEDGED,
            changed_by=SYSTEM,
            reason="Automatic acknowledgement on creation",
        )

        # 9. Acknowledgement notification to customer
        await self._ticket_repo.add_notification_log(NotificationLog(
            ticket_id=ticket.ticket_id,
            recipient_user_id=current_user_id,
            channel=NotificationChannel.EMAIL,
            event_type=EventType.CREATED.value,
            status=NotificationStatus.PENDING,
        ))

        logger.info(
            "ticket_created: number=%s severity=%s priority=%s user=%s",
            ticket_number, severity, priority, current_user_id,
        )
        from src.core.tasks.assignment_task import auto_assign_ticket  # noqa: PLC0415
        auto_assign_ticket.delay(
            ticket_id=ticket.ticket_id,
            ticket_title=ticket.title,
            ticket_priority=ticket.priority.value,
        )
        logger.info(
            "auto_assign_ticket: enqueued for ticket_id=%s", ticket.ticket_id
        )
        return ticket

    # ── STATUS TRANSITION ─────────────────────────────────────────────────────

    async def transition_status(
        self,
        ticket_id: int,
        payload: TicketStatusUpdateRequest,
        current_user_id: str,
        current_user_role: str,
    ) -> Ticket:
        ticket = await self._get_or_404(ticket_id)
        now = datetime.now(timezone.utc)
        old_status = ticket.status
        new_status = payload.new_status

        # Role guard — customers cannot change status
        if UserRole(current_user_role) == UserRole.CUSTOMER:
            raise InsufficientPermissionsError("Customers cannot update ticket status.")

        # Transition matrix guard
        allowed = ALLOWED_TRANSITIONS.get(old_status, [])
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Cannot transition {old_status.value} → {new_status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        # ── SLA side-effects per transition ───────────────────────────────────

        if new_status == TicketStatus.IN_PROGRESS:
            if old_status == TicketStatus.ON_HOLD:
                # Resume resolution SLA — accumulate pause duration
                self._sla_svc.resume_resolution_sla(ticket, now)
            else:
                # First time entering IN_PROGRESS — start resolution SLA
                self._sla_svc.start_resolution_sla(ticket, now)
            # Response SLA always completes when hitting IN_PROGRESS
            self._sla_svc.complete_response_sla(ticket, now)

        elif new_status == TicketStatus.ON_HOLD:
            self._sla_svc.pause_resolution_sla(ticket, now)

        elif new_status == TicketStatus.RESOLVED:
            self._sla_svc.complete_resolution_sla(ticket, now)

        elif new_status == TicketStatus.OPEN and old_status == TicketStatus.CLOSED:
            # Reopen — restart resolution SLA, keep response SLA and escalation_level
            self._sla_svc.restart_resolution_sla(ticket, now)

        # Apply status
        ticket.status = new_status
        ticket = await self._ticket_repo.save(ticket)

        # Timeline + event
        await self._record_transition(
            ticket, from_status=old_status, to_status=new_status,
            changed_by=current_user_id, reason=payload.comment,
        )

        # Notify customer on meaningful transitions
        if new_status in (
            TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED,
            TicketStatus.CLOSED, TicketStatus.OPEN,
        ):
            await self._ticket_repo.add_notification_log(NotificationLog(
                ticket_id=ticket.ticket_id,
                recipient_user_id=ticket.customer_id,
                channel=NotificationChannel.EMAIL,
                event_type=EventType.STATUS_CHANGED.value,
                status=NotificationStatus.PENDING,
            ))

        logger.info(
            "status_changed: id=%s %s→%s by=%s",
            ticket_id, old_status.value, new_status.value, current_user_id,
        )
        return ticket

    # ── ASSIGN ────────────────────────────────────────────────────────────────

    async def assign_ticket(
        self,
        ticket_id: int,
        payload: TicketAssignRequest,
        current_user_id: str,
        current_user_role: str,
    ) -> Ticket:
        ticket = await self._get_or_404(ticket_id)
        role = UserRole(current_user_role)

        if role == UserRole.AGENT and payload.assignee_id != current_user_id:
            raise InsufficientPermissionsError("Agents can only self-assign tickets.")

        old_assignee = ticket.assignee_id
        ticket.assignee_id = payload.assignee_id
        ticket = await self._ticket_repo.save(ticket)

        await self._ticket_repo.add_event(TicketEvent(
            ticket_id=ticket.ticket_id,
            triggered_by_user_id=current_user_id,
            event_type=EventType.ASSIGNED,
            field_name="assignee_id",
            old_value=str(old_assignee) if old_assignee else None,
            new_value=payload.assignee_id,
        ))
        for channel in (NotificationChannel.EMAIL, NotificationChannel.IN_APP):
            await self._ticket_repo.add_notification_log(NotificationLog(
                ticket_id=ticket.ticket_id,
                recipient_user_id=payload.assignee_id,
                channel=channel,
                event_type=EventType.ASSIGNED.value,
                status=NotificationStatus.PENDING,
            ))

        logger.info("assigned: id=%s → %s by %s", ticket_id, payload.assignee_id, current_user_id)
        return ticket

    # ── READ ──────────────────────────────────────────────────────────────────

    async def get_my_tickets(
        self,
        current_user_id: str,
        current_user_role: str,
        filters: TicketListFilters,
    ) -> tuple[int, list[Ticket]]:
        role = UserRole(current_user_role)
        if role == UserRole.CUSTOMER:
            filters.customer_id = current_user_id
        elif role == UserRole.AGENT:
            filters.assignee_id = current_user_id
        return await self._ticket_repo.list_all(filters)

    async def get_ticket_detail(
        self,
        ticket_id: int,
        current_user_id: str,
        current_user_role: str,
    ) -> Ticket:
        ticket = await self._ticket_repo.get_by_id(ticket_id, eager=True)
        if not ticket:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found.")
        if UserRole(current_user_role) == UserRole.CUSTOMER and ticket.customer_id != current_user_id:
            raise InsufficientPermissionsError("You can only view your own tickets.")
        return ticket

    async def get_all_tickets(
        self,
        filters: TicketListFilters,
        current_user_role: str,
    ) -> tuple[int, list[Ticket]]:
        role = UserRole(current_user_role)
        if role not in (UserRole.LEAD, UserRole.ADMIN):
            raise InsufficientPermissionsError("Only team leads and admins can view all tickets.")
        return await self._ticket_repo.list_all(filters)

    