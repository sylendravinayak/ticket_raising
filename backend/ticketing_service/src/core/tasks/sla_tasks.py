import asyncio
import logging
from datetime import datetime, timedelta, timezone

from src.celery_app import celery_app
from src.config.settings import get_settings
from src.constants.enum import (
    EventType, NotificationChannel, NotificationStatus, TicketStatus,
)
from src.core.services.sla_service import SLAService
from src.data.clients.postgres_client import AsyncSessionFactory
from src.data.models.postgres.notification_log import NotificationLog
from src.data.models.postgres.ticket_event import TicketEvent
from src.data.repositories.agent_repository import AgentRepository
from src.data.repositories.sla_repository import SLARepository
from src.data.repositories.ticket_repository import TicketRepository

logger = logging.getLogger(__name__)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_sla_event(ticket, reason: str) -> TicketEvent:
    """
    Build a STATUS_CHANGED TicketEvent for SLA breach/escalation.
    Status does not change — from_status == to_status (same value).
    triggered_by_user_id = None signals a SYSTEM-triggered event.
    """
    return TicketEvent(
        ticket_id=ticket.ticket_id,
        triggered_by_user_id=None,          # None = SYSTEM
        event_type=EventType.SLA_BREACHED,
        field_name="sla",
        from_status=ticket.status.value,    # status unchanged, recorded for timeline
        old_value=ticket.status.value,
        new_value=ticket.status.value,
        reason=reason,
    )


# ══════════════════════════════════════════════════════════════
# TASK 1 — SLA BREACH DETECTION (every 5 minutes)
# ══════════════════════════════════════════════════════════════

@celery_app.task(name="tasks.detect_sla_breaches", bind=True, max_retries=3)
def detect_sla_breaches(self):
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
        sla_svc = SLAService(SLARepository(db))

        leads = await agent_repo.get_available_leads()
        lead_ids = [a.user_id for a in leads]

        # ── Response SLA breach ───────────────────────────────────────────────
        response_candidates = await repo.get_response_sla_candidates(now)

        for ticket in response_candidates:
            if not sla_svc.check_response_breach(ticket, now):
                continue
            try:
                ticket.response_sla_breached_at = now
                ticket.escalation_level += 1
                await repo.save(ticket)

                # Write breach event into ticket_events (IS the timeline row)
                await repo.add_event(_make_sla_event(
                    ticket,
                    reason=f"Response SLA breached — escalation level {ticket.escalation_level}",
                ))

                # Notify all team leads
                for lead_id in lead_ids:
                    for ch in (NotificationChannel.EMAIL, NotificationChannel.IN_APP):
                        await repo.add_notification_log(NotificationLog(
                            ticket_id=ticket.ticket_id,
                            recipient_user_id=lead_id,
                            channel=ch,
                            event_type=EventType.SLA_BREACHED.value,
                            status=NotificationStatus.PENDING,
                        ))

                await db.commit()
                logger.info(
                    "response_sla_breached: ticket_id=%s level=%s",
                    ticket.ticket_id, ticket.escalation_level,
                )
            except Exception as exc:
                await db.rollback()
                logger.error("response_breach failed ticket_id=%s: %s", ticket.ticket_id, exc)

        # ── Resolution SLA breach ─────────────────────────────────────────────
        resolution_candidates = await repo.get_resolution_sla_candidates(now)

        for ticket in resolution_candidates:
            if not sla_svc.check_resolution_breach(ticket, now):
                continue
            try:
                ticket.resolution_sla_breached_at = now
                ticket.escalation_level += 1
                await repo.save(ticket)

                # Write breach event into ticket_events (IS the timeline row)
                await repo.add_event(_make_sla_event(
                    ticket,
                    reason=f"Resolution SLA breached — escalation level {ticket.escalation_level}",
                ))

                # Notify all team leads
                for lead_id in lead_ids:
                    for ch in (NotificationChannel.EMAIL, NotificationChannel.IN_APP):
                        await repo.add_notification_log(NotificationLog(
                            ticket_id=ticket.ticket_id,
                            recipient_user_id=lead_id,
                            channel=ch,
                            event_type=EventType.SLA_BREACHED.value,
                            status=NotificationStatus.PENDING,
                        ))

                await db.commit()
                logger.info(
                    "resolution_sla_breached: ticket_id=%s level=%s",
                    ticket.ticket_id, ticket.escalation_level,
                )
            except Exception as exc:
                await db.rollback()
                logger.error("resolution_breach failed ticket_id=%s: %s", ticket.ticket_id, exc)


# ══════════════════════════════════════════════════════════════
# TASK 2 — AUTO CLOSE (every hour)
# ═════════��════════════════════════════════════════════════════

@celery_app.task(name="tasks.auto_close_resolved_tickets", bind=True, max_retries=3)
def auto_close_resolved_tickets(self):
    try:
        _run(_auto_close_async())
    except Exception as exc:
        logger.exception("auto_close_resolved_tickets failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


async def _auto_close_async() -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=get_settings().AUTO_CLOSE_AFTER_HOURS)

    async with AsyncSessionFactory() as db:
        repo = TicketRepository(db)

        tickets = await repo.get_auto_closeable(cutoff)
        if not tickets:
            logger.debug("auto_close: no candidates at %s", now)
            return

        for ticket in tickets:
            try:
                old_status = ticket.status
                ticket.status = TicketStatus.CLOSED
                ticket.auto_closed = True
                await repo.save(ticket)

                # Write STATUS_CHANGED event — this IS the timeline row
                await repo.add_event(TicketEvent(
                    ticket_id=ticket.ticket_id,
                    triggered_by_user_id=None,          # None = SYSTEM
                    event_type=EventType.STATUS_CHANGED,
                    field_name="status",
                    from_status=old_status.value,       # timeline: where it came from
                    old_value=old_status.value,
                    new_value=TicketStatus.CLOSED.value,
                    reason="Auto-closed after 72h in RESOLVED",
                ))

                # Notify customer
                await repo.add_notification_log(NotificationLog(
                    ticket_id=ticket.ticket_id,
                    recipient_user_id=ticket.customer_id,
                    channel=NotificationChannel.EMAIL,
                    event_type=EventType.AUTO_CLOSED.value,
                    status=NotificationStatus.PENDING,
                ))

                await db.commit()
                logger.info(
                    "auto_closed: ticket_id=%s number=%s",
                    ticket.ticket_id, ticket.ticket_number,
                )
            except Exception as exc:
                await db.rollback()
                logger.error("auto_close failed ticket_id=%s: %s", ticket.ticket_id, exc)