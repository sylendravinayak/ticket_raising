"""
Celery task: auto_assign_ticket

Triggered immediately after a ticket is created.
Runs the LangChain ReAct agent (Groq) to pick + assign the best agent.

Flow:
  ticket_service.create_ticket()
      → auto_assign_ticket.delay(ticket_id, title, priority)
          → [Redis queue]
              → Celery worker
                  → create_react_agent (LLM)
                      → get_available_agents (DB)
                      → get_agent_resolution_history (DB)
                      → assign_ticket_to_agent (DB)
"""

import asyncio
import logging

from src.celery_app import celery_app
from src.control.assignment_agent.workflow import run_auto_assign

logger = logging.getLogger(__name__)

# System identity used when the auto-assign is triggered without a human assigner
SYSTEM_ASSIGNER_ID = "SYSTEM"
SYSTEM_ASSIGNER_ROLE = "admin"


def _run(coro):
    """
    Run an async coroutine from a sync Celery task.
    Matches the pattern used in sla_tasks.py.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


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
    Celery task that triggers the AI assignment agent.

    Args:
        ticket_id      : PK of the newly created ticket
        ticket_title   : title string (for LLM context)
        ticket_priority: priority enum value e.g. "P1"
        assigner_id    : UUID of assigner or "SYSTEM"
        assigner_role  : role of the assigner e.g. "admin"

    Returns:
        dict with ticket_id, agent_response, steps
    """
    logger.info(
        "auto_assign_ticket: started ticket_id=%s priority=%s",
        ticket_id, ticket_priority,
    )
    try:
        result = _run(
            run_auto_assign(
                ticket_id=ticket_id,
                ticket_title=ticket_title,
                ticket_priority=ticket_priority,
                assigner_id=assigner_id,
                assigner_role=assigner_role,
            )
        )
        logger.info(
            "auto_assign_ticket: completed ticket_id=%s response=%s",
            ticket_id, result.get("agent_response", "")[:120],
        )
        return result

    except Exception as exc:
        logger.exception("auto_assign_ticket failed for ticket_id=%s: %s", ticket_id, exc)
        raise self.retry(exc=exc)
