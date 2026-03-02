"""
AI Assignment Agent using LangChain's create_react_agent + Groq LLM.

This agent has two tools:
  1. get_available_agents  — queries agent_profiles from the DB
  2. assign_ticket_to_agent — calls TicketService.assign_ticket
"""

import json
import logging
from typing import Any

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from src.config.settings import get_settings
from src.data.clients.postgres_client import AsyncSessionFactory
from src.data.repositories.agent_repository import AgentRepository
from src.data.repositories.ticket_repository import TicketRepository
from src.core.services.ticket_service import TicketService
from src.schemas.ticket_schema import TicketAssignRequest

logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def get_available_agents(dummy: str = "") -> str:
    """
    Query the database for all available support agents.
    Returns a JSON list of agents with their user_id, display_name,
    max_open_tickets, and customer_tier_id.
    """
    async with AsyncSessionFactory() as session:
        repo = AgentRepository(session)
        agents = await repo.get_available_agents()

    if not agents:
        return json.dumps({"agents": [], "message": "No available agents found."})

    return json.dumps({
        "agents": [
            {
                "user_id": a.user_id,
                "display_name": a.display_name,
                "max_open_tickets": a.max_open_tickets,
                "customer_tier_id": a.customer_tier_id,
                "is_available": a.is_available,
            }
            for a in agents
        ]
    })


@tool
async def assign_ticket_to_agent(input_json: str) -> str:
    """
    Assign a ticket to a specific agent.

    Input MUST be a JSON string with these fields:
      - ticket_id     (int)   : the ticket to assign
      - assignee_id   (str)   : the user_id (UUID string) of the chosen agent
      - assigner_id   (str)   : the user_id of the team_lead/admin performing assignment
      - assigner_role (str)   : role of the assigner, e.g. "team_lead" or "admin"

    Example input:
      {"ticket_id": 42, "assignee_id": "uuid-...", "assigner_id": "uuid-...", "assigner_role": "team_lead"}

    Returns a JSON string with the result.
    """
    try:
        data = json.loads(input_json)
        ticket_id: int = int(data["ticket_id"])
        assignee_id: str = str(data["assignee_id"])
        assigner_id: str = str(data["assigner_id"])
        assigner_role: str = str(data["assigner_role"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        return json.dumps({"error": f"Invalid input: {exc}"})

    async with AsyncSessionFactory() as session:
        ticket_repo = TicketRepository(session)
        agent_repo = AgentRepository(session)
        svc = TicketService(ticket_repo=ticket_repo, agent_repo=agent_repo)

        try:
            ticket = await svc.assign_ticket(
                ticket_id=ticket_id,
                payload=TicketAssignRequest(assignee_id=assignee_id),
                current_user_id=assigner_id,
                current_user_role=assigner_role,
            )
            await session.commit()
        except Exception as exc:
            logger.error("assign_ticket_to_agent failed: %s", exc)
            return json.dumps({"error": str(exc)})

    return json.dumps({
        "success": True,
        "ticket_id": ticket.ticket_id,
        "ticket_number": ticket.ticket_number,
        "assignee_id": ticket.assignee_id,
        "status": ticket.status.value,
    })
