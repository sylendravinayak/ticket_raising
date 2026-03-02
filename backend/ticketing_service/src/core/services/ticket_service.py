

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.clients.auth_client import AuthServiceClient, UserDTO
from src.config.settings import get_settings
from src.constants.enum import (
    EventType,
    NotificationChannel,
    NotificationStatus,
    Priority,
    Severity,
    TicketStatus,
    UserRole,
)
from src.core.exceptions.base import (
    InsufficientPermissionsError,
    InvalidStatusTransitionError,
    TicketNotFoundError,
)
from src.core.services.classification_service import ClassificationService
from src.core.services.sla_service import SLAService
from src.data.models.postgres.escalation import EscalationHistory
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


ALLOWED_TRANSITIONS: dict[TicketStatus, list[TicketStatus]] = {
    TicketStatus.NEW: [TicketStatus.ACKNOWLEDGED],
    TicketStatus.ACKNOWLEDGED: [TicketStatus.IN_PROGRESS],
    TicketStatus.IN_PROGRESS: [TicketStatus.ON_HOLD, TicketStatus.RESOLVED],
    TicketStatus.ON_HOLD: [TicketStatus.IN_PROGRESS],
    TicketStatus.RESOLVED: [TicketStatus.CLOSED],
    TicketStatus.CLOSED: [TicketStatus.REOPENED],
    TicketStatus.REOPENED: [TicketStatus.ACKNOWLEDGED],
}


class TicketService:
    def __init__(
        self,
        db: AsyncSession,
        auth_client: AuthServiceClient,
    ) -> None:
        self.db = db
        self._auth = auth_client
        self._ticket_repo = TicketRepository(db)
        self._sla_repo = SLARepository(db)
        self._keyword_repo = KeywordRepository(db)
        self._agent_repo = AgentRepository(db)
        self._classifier = ClassificationService(self._keyword_repo)
        self._sla_svc = SLAService(self._sla_repo)


    async def create_ticket(
        self,
        payload: TicketCreateRequest,
        current_user_id: int,
    ) -> Ticket:
        """
        Full creation pipeline:
          classify → map priority → SLA lookup → deadlines
          → persist ticket + event + notification in one transaction.
        """
        now = datetime.now(timezone.utc)

        # 1. Fetch current user from Auth Service (needed for tier lookup)
        customer: UserDTO = await self._auth.get_user(current_user_id)

        # 2. Classify
        classification = await self._classifier.classify(payload.title, payload.description)
        severity: Severity = classification.severity
        priority: Priority = classification.priority

        # 3. SLA lookup + deadline calculation
        deadlines = await self._sla_svc.resolve_deadlines(
            customer_tier_id=customer.customer_tier_id,
            severity=severity,
            priority=priority,
            from_dt=now,
        )

        # 4. Generate ticket number
        ticket_number = await self._ticket_repo.next_ticket_number()

        # 5. Build Ticket ORM object
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
            sla_id=deadlines.sla_id,
            customer_tier_id=customer.customer_tier_id,
            response_due_at=deadlines.response_due_at,
            resolution_due_at=deadlines.resolution_due_at,
            is_breached=False,
            is_escalated=False,
            total_hold_minutes=0,
        )
        ticket = await self._ticket_repo.create(ticket)

        # 6. Attachments (stubbed URLs)
        for url in payload.attachments:
            att = TicketAttachment(
                ticket_id=ticket.ticket_id,
                file_name=url.split("/")[-1],
                file_url=url,
                uploaded_by_user_id=current_user_id,
            )
            await self._ticket_repo.add_attachment(att)

        # 7. TicketEvent — CREATED
        await self._ticket_repo.add_event(TicketEvent(
            ticket_id=ticket.ticket_id,
            triggered_by_user_id=current_user_id,
            event_type=EventType.CREATED,
            field_name="status",
            old_value=None,
            new_value=TicketStatus.NEW.value,
        ))

        # 8. NotificationLog — customer acknowledgement (PENDING)
        await self._ticket_repo.add_notification_log(NotificationLog(
            ticket_id=ticket.ticket_id,
            recipient_user_id=current_user_id,
            channel=NotificationChannel.EMAIL,
            event_type=EventType.CREATED.value,
            status=NotificationStatus.PENDING,
        ))

        logger.info(
            "ticket_created: number=%s severity=%s priority=%s sla_id=%s user_id=%s",
            ticket_number, severity, priority, deadlines.sla_id, current_user_id,
        )
        return ticket

    # ══════════════════════════════════════════
    # STEP 2 — STATUS TRANSITION
    # ══════════════════════════════════════════

    async def transition_status(
    self,
    ticket_id: int,
    payload: TicketStatusUpdateRequest,
    current_user_id: str,          
    current_user_role: str,         
) -> Ticket:
        ticket = await self._get_or_404(ticket_id)
        old_status = ticket.status
        new_status = payload.new_status
        now = datetime.now(timezone.utc)

        # Role-based guard: users (customers) cannot change status
        role = UserRole(current_user_role)
        if role == UserRole.CUSTOMER:
            raise InsufficientPermissionsError(
                "Customers cannot update ticket status."
            )

        # Guard: valid state machine transition?
        allowed = ALLOWED_TRANSITIONS.get(old_status, [])
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Cannot transition from {old_status.value} → {new_status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        # ── Side effects per transition ───────────────────────────────────────

        if new_status == TicketStatus.ON_HOLD:
            ticket.hold_started_at = now

        elif old_status == TicketStatus.ON_HOLD and new_status == TicketStatus.IN_PROGRESS:
            if ticket.hold_started_at:
                elapsed = now - ticket.hold_started_at
                elapsed_minutes = int(elapsed.total_seconds() // 60)
                ticket.total_hold_minutes += elapsed_minutes
                ticket.resolution_due_at = (
                    ticket.resolution_due_at + elapsed
                    if ticket.resolution_due_at
                    else now + timedelta(minutes=get_settings().DEFAULT_RESOLUTION_TIME_MINUTES)
                )
                ticket.hold_started_at = None

        elif new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = now

        elif new_status == TicketStatus.CLOSED:
            ticket.closed_at = now

        elif new_status == TicketStatus.REOPENED:
            ticket.is_breached = False
            ticket.is_escalated = False
            ticket.resolved_at = None
            ticket.closed_at = None

        ticket.status = new_status
        ticket = await self._ticket_repo.save(ticket)

        # Audit event
        await self._ticket_repo.add_event(TicketEvent(
            ticket_id=ticket.ticket_id,
            triggered_by_user_id=current_user_id,
            event_type=EventType.STATUS_CHANGED,
            field_name="status",
            old_value=old_status.value,
            new_value=new_status.value,
        ))

        # Notify customer
        await self._ticket_repo.add_notification_log(NotificationLog(
            ticket_id=ticket.ticket_id,
            recipient_user_id=ticket.customer_id,
            channel=NotificationChannel.EMAIL,
            event_type=EventType.STATUS_CHANGED.value,
            status=NotificationStatus.PENDING,
        ))

        logger.info(
            "ticket_status_changed: id=%s %s→%s by user=%s",
            ticket_id, old_status.value, new_status.value, current_user_id,
        )
        return ticket

   
    


    async def get_my_tickets(
        self,
        current_user_id: str,
        current_user_role: str,
        filters: TicketListFilters,
    ) -> tuple[int, list[Ticket]]:
        """
        Returns tickets relevant to the caller based on their role:
          USER          → tickets they raised (customer_id = me)
          SUPPORT_AGENT → tickets assigned to them (assignee_id = me)
          TEAM_LEAD     → all tickets
          ADMIN         → all tickets
        """
        role = UserRole(current_user_role)

        if role == UserRole.CUSTOMER:
            # Customer sees only tickets they created
            filters.customer_id = current_user_id
            return await self._ticket_repo.list_all(filters)

        elif role == UserRole.AGENT:
            # Agent sees only tickets assigned to them
            filters.assignee_id = current_user_id
            return await self._ticket_repo.list_all(filters)

        else:
            # TEAM_LEAD / ADMIN see everything
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

        role = UserRole(current_user_role)
        # Users can only view their own tickets
        if role == UserRole.CUSTOMER and ticket.customer_id != current_user_id:
            raise InsufficientPermissionsError("You can only view your own tickets.")

        return ticket


    async def get_ticket_logs(self, ticket_id: int) -> list[TicketEvent]:
        ticket = await self._ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found.")
        return await self._ticket_repo.get_events(ticket_id)

    async def get_all_tickets(
        self,
        filters: TicketListFilters,
        current_user_role: str,
    ) -> tuple[int, list[Ticket]]:
        role = UserRole(current_user_role)
        if role not in (UserRole.LEAD, UserRole.ADMIN):
            raise InsufficientPermissionsError(
                "Only team leads and admins can view all tickets."
            )
        return await self._ticket_repo.list_all(filters)

    async def assign_ticket(
        self,
        ticket_id: int,
        payload: TicketAssignRequest,
        current_user_id: str,
        current_user_role: str,
    ) -> Ticket:
        ticket = await self._get_or_404(ticket_id)
        old_assignee = ticket.assignee_id
        new_assignee = payload.assignee_id

        role = UserRole(current_user_role)
        # Agents can only self-assign
        if role == UserRole.AGENT and new_assignee != current_user_id:
            raise InsufficientPermissionsError(
                "Agents can only self-assign. Use your own user_id as assignee_id."
            )

        ticket.assignee_id = new_assignee
        ticket = await self._ticket_repo.save(ticket)

        await self._ticket_repo.add_event(TicketEvent(
            ticket_id=ticket.ticket_id,
            triggered_by_user_id=current_user_id,
            event_type=EventType.ASSIGNED,
            field_name="assignee_id",
            old_value=str(old_assignee) if old_assignee else None,
            new_value=str(new_assignee),
        ))

        for channel in (NotificationChannel.EMAIL, NotificationChannel.IN_APP):
            await self._ticket_repo.add_notification_log(NotificationLog(
                ticket_id=ticket.ticket_id,
                recipient_user_id=new_assignee,
                channel=channel,
                event_type=EventType.ASSIGNED.value,
                status=NotificationStatus.PENDING,
            ))

        logger.info(
            "ticket_assigned: id=%s old=%s new=%s by user=%s",
            ticket_id, old_assignee, new_assignee, current_user_id,
        )
        return ticket

    async def _get_or_404(self, ticket_id: int) -> Ticket:
        ticket = await self._ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found.")
        return ticket