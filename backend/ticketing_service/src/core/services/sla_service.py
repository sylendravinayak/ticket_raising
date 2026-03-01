"""
SLA service — deadline calculation and breach/escalation logic.
Plain datetime arithmetic (no business hours yet).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.config.settings import settings
from src.constants.enum import Priority, Severity
from src.data.repositories.sla_repository import SLARepository

logger = logging.getLogger(__name__)


@dataclass
class SLADeadlines:
    sla_id: int | None
    response_due_at: datetime
    resolution_due_at: datetime
    escalation_after_minutes: int
    used_default: bool = False


class SLAService:
    def __init__(self, sla_repo: SLARepository) -> None:
        self._repo = sla_repo

    async def resolve_deadlines(
        self,
        customer_tier_id: int | None,
        severity: Severity,
        priority: Priority,
        from_dt: datetime | None = None,
    ) -> SLADeadlines:
        """
        Look up SLARule for (tier, severity, priority) and compute deadlines.
        Falls back to configured defaults if no rule found.
        """
        now = from_dt or datetime.now(timezone.utc)
        sla = None
        rule = None

        if customer_tier_id is not None:
            sla = await self._repo.get_active_sla_for_tier(customer_tier_id)
            if sla:
                rule = await self._repo.get_rule(sla.sla_id, severity, priority)

        if rule is None:
            logger.warning(
                "sla_service: no rule found tier=%s sev=%s pri=%s — using defaults",
                customer_tier_id, severity, priority,
            )
            return SLADeadlines(
                sla_id=sla.sla_id if sla else None,
                response_due_at=now + timedelta(minutes=settings.DEFAULT_RESPONSE_TIME_MINUTES),
                resolution_due_at=now + timedelta(minutes=settings.DEFAULT_RESOLUTION_TIME_MINUTES),
                escalation_after_minutes=settings.DEFAULT_ESCALATION_AFTER_MINUTES,
                used_default=True,
            )

        return SLADeadlines(
            sla_id=sla.sla_id,
            response_due_at=now + timedelta(minutes=rule.response_time_minutes),
            resolution_due_at=now + timedelta(minutes=rule.resolution_time_minutes),
            escalation_after_minutes=rule.escalation_after_minutes,
        )

    async def recalculate_for_reopen(
        self,
        customer_tier_id: int | None,
        severity: Severity,
        priority: Priority,
    ) -> SLADeadlines:
        """Fresh SLA deadlines from right now — used on REOPENED transition."""
        return await self.resolve_deadlines(customer_tier_id, severity, priority)