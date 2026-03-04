"""
Celery task: auto_assign_ticket + check_lead_timeout

Step 1 — AI tries routing.  If success → assign agent (queue_type=DIRECT, routing_status=SUCCESS).
Step 2 — If AI fails → assign to Lead with timeout (queue_type=DIRECT, routing_status=AI_FAILED).
Step 3 — Beat job: if Lead doesn't reassign within LEAD_TIMEOUT_MINUTES →
         move ticket to OPEN queue (assignee_id=NULL, queue_type=OPEN, status=OPEN).
"""

import logging
from datetime import datetime, timedelta, timezone

from src.celery_app import celery_app
from src.config.settings import get_settings
from src.constants.enum import QueueType, RoutingStatus, TicketStatus
from src.control.assignment_agent.workflow import run_auto_assign
from src.data.clients.postgres_client import AsyncSessionFactory
from src.data.models.postgres.ticket_event import TicketEvent
from src.constants.enum import EventType
from src.data.repositories.agent_repository import AgentRepository
from src.data.repositories.ticket_event_repository import TicketEventRepository
from src.data.repositories.ticket_repository import TicketRepository

from src.core.tasks._loop import run_async

logger = logging.getLogger(__name__)

SYSTEM_ASSIGNER_ID = "SYSTEM"
SYSTEM_ASSIGNER_ROLE = "admin"



async def _mark_ai_success(ticket_id: int, agent_user_id: str | None) -> None:
    """Set routing_status=SUCCESS, queue_type=DIRECT on the ticket."""
    async with AsyncSessionFactory() as session:
        repo = TicketRepository(session)
        ticket = await repo.get_by_id(ticket_id)
        if ticket:
            ticket.routing_status = RoutingStatus.SUCCESS.value
            ticket.queue_type = QueueType.DIRECT.value
            if agent_user_id is not None:
                ticket.assigned_agent_id = agent_user_id
            await repo.save(ticket)
            await session.commit()


async def _fallback_to_lead(ticket_id: int) -> None:
    """
    AI failed — assign the ticket to the team lead.
    Sets routing_status=AI_FAILED, queue_type=DIRECT, lead_assigned_at=now.
    """
    now = datetime.now(timezone.utc)
    async with AsyncSessionFactory() as session:
        agent_repo = AgentRepository(session)
        ticket_repo = TicketRepository(session)
        event_repo = TicketEventRepository(session)

        lead = await agent_repo.get_lead_agent()
        ticket = await ticket_repo.get_by_id(ticket_id)
        if not ticket:
            logger.error("_fallback_to_lead: ticket %s not found", ticket_id)
            return

        ticket.routing_status = RoutingStatus.AI_FAILED.value
        ticket.queue_type = QueueType.DIRECT.value
        ticket.lead_assigned_at = now

        if lead:
            ticket.assignee_id = str(lead.user_id)
            ticket.assigned_agent_id = lead.user_id
            logger.info(
                "AI failed → assigned to lead %s (user_id=%s) for ticket %s",
                lead.display_name, lead.user_id, ticket_id,
            )
            # Record assignment event
            await event_repo.add(TicketEvent(
                ticket_id=ticket.ticket_id,
                triggered_by_user_id=None,
                event_type=EventType.ASSIGNED,
                field_name="assignee_id",
                old_value=None,
                new_value=str(lead.user_id),
                reason="AI routing failed — assigned to team lead for manual triage",
            ))
        else:
            # No lead available — go straight to OPEN queue
            logger.warning(
                "AI failed & no lead available → ticket %s → OPEN queue", ticket_id,
            )
            ticket.assignee_id = None
            ticket.assigned_agent_id = None
            ticket.queue_type = QueueType.OPEN.value
            ticket.status = TicketStatus.OPEN

        await ticket_repo.save(ticket)
        await session.commit()


async def _move_to_open_queue(ticket_id: int) -> None:
    """
    Lead timed out — clear assignment, set queue_type=OPEN, status=OPEN.
    """
    async with AsyncSessionFactory() as session:
        repo = TicketRepository(session)
        event_repo = TicketEventRepository(session)
        ticket = await repo.get_by_id(ticket_id)
        if not ticket:
            return
        old_assignee = ticket.assignee_id
        ticket.assignee_id = None
        ticket.assigned_agent_id = None
        ticket.queue_type = QueueType.OPEN.value
        ticket.status = TicketStatus.OPEN
        await repo.save(ticket)

        await event_repo.add(TicketEvent(
            ticket_id=ticket.ticket_id,
            triggered_by_user_id=None,
            event_type=EventType.STATUS_CHANGED,
            field_name="status",
            old_value=TicketStatus.ACKNOWLEDGED.value,
            new_value=TicketStatus.OPEN.value,
            reason=(
                f"Lead (assignee {old_assignee}) did not assign within timeout — "
                "moved to OPEN queue"
            ),
        ))
        await session.commit()


# ── Celery tasks ──────────────────────────────────────────────────────────────

@celery_app.task(
    name="tasks.auto_assign_ticket",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def auto_assign_ticket(
    self,
    ticket_id: int,
    ticket_title: str,
    ticket_priority: str,
    assigner_id: str = SYSTEM_ASSIGNER_ID,
    assigner_role: str = SYSTEM_ASSIGNER_ROLE,
) -> dict:
    """
    Step 1: AI tries to route.
    Step 2: On failure → fallback to lead with timeout.
    """
    logger.info(
        "auto_assign_ticket: started ticket_id=%s priority=%s",
        ticket_id, ticket_priority,
    )
    try:
        result = run_async(
            run_auto_assign(
                ticket_id=ticket_id,
                ticket_title=ticket_title,
                ticket_priority=ticket_priority,
                assigner_id=assigner_id,
                assigner_role=assigner_role,
            )
        )

        # AI succeeded — mark routing as SUCCESS
        run_async(_mark_ai_success(ticket_id, agent_user_id=None))

        logger.info(
            "auto_assign_ticket: AI succeeded for ticket_id=%s response=%s",
            ticket_id, result.get("agent_response", "")[:120],
        )
        return result

    except Exception as exc:
        logger.warning(
            "auto_assign_ticket: AI failed for ticket_id=%s (%s) — falling back to lead",
            ticket_id, exc,
        )
        try:
            run_async(_fallback_to_lead(ticket_id))
            return {
                "ticket_id": ticket_id,
                "agent_response": f"AI routing failed: {exc}. Assigned to team lead.",
                "routing_status": RoutingStatus.AI_FAILED.value,
            }
        except Exception as fallback_exc:
            logger.exception(
                "auto_assign_ticket: fallback also failed for ticket_id=%s", ticket_id,
            )
            raise self.retry(exc=fallback_exc)


@celery_app.task(name="tasks.check_lead_timeout")
def check_lead_timeout() -> dict:
    """
    Beat job: find tickets assigned to leads past the timeout window
    and move them to the OPEN queue.
    """
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.LEAD_TIMEOUT_MINUTES)
    logger.info("check_lead_timeout: cutoff=%s", cutoff.isoformat())

    async def _check():
        async with AsyncSessionFactory() as session:
            repo = TicketRepository(session)
            tickets = await repo.get_lead_timed_out_tickets(cutoff)
            return [t.ticket_id for t in tickets]

    ticket_ids = run_async(_check())

    moved = []
    for tid in ticket_ids:
        try:
            run_async(_move_to_open_queue(tid))
            moved.append(tid)
            logger.info("check_lead_timeout: ticket %s → OPEN queue", tid)
        except Exception:
            logger.exception("check_lead_timeout: failed to move ticket %s", tid)

    return {"moved_to_open_queue": moved}
