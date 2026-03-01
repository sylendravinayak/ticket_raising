"""
Celery Beat tasks for SLA breach detection, escalation, and auto-close.

Each task:
  1. Opens its own async DB session (not a FastAPI request session)
  2. Applies business rules
  3. Commits atomically per ticket to minimise lock contention
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from src.celery_app import celery_app
from src.config.settings import settings
from src.constants.enum import (
    EventType,
    NotificationChannel,
    NotificationStatus,
    TicketStatus,
)
from src.data.clients.postgres_client import AsyncSessionFactory
from src.data.models.postgres.escalation import EscalationHistory
from src.data.models.postgres.notification_log import NotificationLog
from src.data.models.postgres.ticket_event import TicketEvent
from src.data.repositories.agent_repository import AgentRepository
from src.data.repositories.sla_repository import SLARepository
from src.data.repositories.ticket_repository import TicketRepository

logger = logging.getLogger(__name__)


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ══════════════════════════════════════════════════════════════
# TASK 1 — SLA BREACH DETECTION (every 5 minutes)
# ══════════════════════════════════════════════════════════════

@celery_app.task(name="tasks.detect_sla_breaches", bind=True, max_retries=3)
def detect_sla_breaches(self):
    """Mark overdue tickets as breached and notify team leads."""
    try:
        _run(_detect_sla_breaches_async())
    except Exception as exc:
        logger.exception("detect_sla_breaches failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


async def _detect_sla_breaches_async() -> None:
    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as db:
        repo = TicketRepository(db)
        agent_repo = AgentRepository(db)

        tickets = await repo.get_breachable(now)
        if not tickets:
            logger.debug("sla_breach_check: no overdue tickets found at %s", now)
            return

        leads = await agent_repo.get_available_leads()
        lead_ids = [a.user_id for a in leads]

        for ticket in tickets:
            try:
                ticket.is_breached = True
                await repo.save(ticket)

                # TicketEvent — SLA_BREACHED
                await repo.add_event(TicketEvent(
                    ticket_id=ticket.ticket_id,
                    triggered_by_user_id=None,  # system-triggered
                    event_type=EventType.SLA_BREACHED,
                    field_name="is_breached",
                    old_value="false",
                    new_value="true",
                ))

                # Notify all team leads (EMAIL + IN_APP)
                for lead_id in lead_ids:
                    for channel in (NotificationChannel.EMAIL, NotificationChannel.IN_APP):
                        await repo.add_notification_log(NotificationLog(
                            ticket_id=ticket.ticket_id,
                            recipient_user_id=lead_id,
                            channel=channel,
                            event_type=EventType.SLA_BREACHED.value,
                            status=NotificationStatus.PENDING,
                        ))

                await db.commit()
                logger.info("sla_breached: ticket_id=%s number=%s", ticket.ticket_id, ticket.ticket_number)

            except Exception as exc:
                await db.rollback()
                logger.error("sla_breach: failed for ticket_id=%s: %s", ticket.ticket_id, exc)


@celery_app.task(name="tasks.detect_escalations", bind=True, max_retries=3)
def detect_escalations(self):
    """Escalate breached tickets that have exceeded escalationAfterMinutes."""
    try:
        _run(_detect_escalations_async())
    except Exception as exc:
        logger.exception("detect_escalations failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


async def _detect_escalations_async() -> None:
    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as db:
        repo = TicketRepository(db)
        sla_repo = SLARepository(db)
        agent_repo = AgentRepository(db)

        tickets = await repo.get_escalatable(now)
        if not tickets:
            logger.debug("escalation_check: no escalatable tickets at %s", now)
            return

        leads = await agent_repo.get_available_leads()
        if not leads:
            logger.warning("escalation_check: no available leads to escalate to")
            return

        lead_ids = [a.user_id for a in leads]
        # Primary lead is the first available one
        primary_lead_id = lead_ids[0]

        for ticket in tickets:
            # Double-check: skip if already escalated (race condition guard)
            if ticket.is_escalated:
                continue

            # Determine escalation_after_minutes from SLA rule
            escalation_after = settings.DEFAULT_ESCALATION_AFTER_MINUTES
            if ticket.sla_id:
                rule = await sla_repo.get_rule(ticket.sla_id, ticket.severity, ticket.priority)
                if rule:
                    escalation_after = rule.escalation_after_minutes

            # Find when ticket was breached — use resolution_due_at as breach time proxy
            if ticket.resolution_due_at is None:
                continue

            breach_time = ticket.resolution_due_at
            grace_expires_at = breach_time + timedelta(minutes=escalation_after)

            if now < grace_expires_at:
                logger.debug(
                    "escalation_check: ticket_id=%s grace not expired yet (expires %s)",
                    ticket.ticket_id, grace_expires_at,
                )
                continue

            try:
                ticket.is_escalated = True
                await repo.save(ticket)

                # EscalationHistory record
                await repo.add_escalation(EscalationHistory(
                    ticket_id=ticket.ticket_id,
                    escalated_by_user_id=None,  # system-triggered
                    escalated_to_user_id=primary_lead_id,
                    reason="SLA Breach — automatic escalation after grace period",
                ))

                # TicketEvent — ESCALATED
                await repo.add_event(TicketEvent(
                    ticket_id=ticket.ticket_id,
                    triggered_by_user_id=None,
                    event_type=EventType.ESCALATED,
                    field_name="is_escalated",
                    old_value="false",
                    new_value="true",
                ))

                # Notify all leads (EMAIL + IN_APP)
                for lead_id in lead_ids:
                    for channel in (NotificationChannel.EMAIL, NotificationChannel.IN_APP):
                        await repo.add_notification_log(NotificationLog(
                            ticket_id=ticket.ticket_id,
                            recipient_user_id=lead_id,
                            channel=channel,
                            event_type=EventType.ESCALATED.value,
                            status=NotificationStatus.PENDING,
                        ))

                await db.commit()
                logger.info(
                    "ticket_escalated: ticket_id=%s → lead_id=%s",
                    ticket.ticket_id, primary_lead_id,
                )

            except Exception as exc:
                await db.rollback()
                logger.error("escalation: failed for ticket_id=%s: %s", ticket.ticket_id, exc)


# ══════════════════════════════════════════════════════════════
# TASK 3 — AUTO CLOSE (every hour)
# ══════════════════════════════════════════════════════════════

@celery_app.task(name="tasks.auto_close_resolved_tickets", bind=True, max_retries=3)
def auto_close_resolved_tickets(self):
    """Move RESOLVED tickets to CLOSED after 72 hours of inactivity."""
    try:
        _run(_auto_close_async())
    except Exception as exc:
        logger.exception("auto_close_resolved_tickets failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


async def _auto_close_async() -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=settings.AUTO_CLOSE_AFTER_HOURS)

    async with AsyncSessionFactory() as db:
        repo = TicketRepository(db)
        tickets = await repo.get_auto_closeable(cutoff)

        if not tickets:
            logger.debug("auto_close: no resolved tickets older than %sh", settings.AUTO_CLOSE_AFTER_HOURS)
            return

        for ticket in tickets:
            try:
                ticket.status = TicketStatus.CLOSED
                ticket.closed_at = now
                await repo.save(ticket)

                # TicketEvent — CLOSED (system)
                await repo.add_event(TicketEvent(
                    ticket_id=ticket.ticket_id,
                    triggered_by_user_id=None,
                    event_type=EventType.CLOSED,
                    field_name="status",
                    old_value=TicketStatus.RESOLVED.value,
                    new_value="AUTO_CLOSED",
                ))

                # Notify customer
                await repo.add_notification_log(NotificationLog(
                    ticket_id=ticket.ticket_id,
                    recipient_user_id=ticket.customer_id,
                    channel=NotificationChannel.EMAIL,
                    event_type=EventType.CLOSED.value,
                    status=NotificationStatus.PENDING,
                ))

                await db.commit()
                logger.info(
                    "auto_closed: ticket_id=%s number=%s resolved_at=%s",
                    ticket.ticket_id, ticket.ticket_number, ticket.resolved_at,
                )

            except Exception as exc:
                await db.rollback()
                logger.error("auto_close: failed for ticket_id=%s: %s", ticket.ticket_id, exc)