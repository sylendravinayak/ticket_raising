"""
AI Assignment Agent using LangChain's create_react_agent + Groq LLM.

This agent has three tools:
  1. get_available_agents          — queries agent_profiles from the DB
  2. get_agent_resolution_history  — returns what kinds of tickets each agent resolved before
  3. assign_ticket_to_agent        — calls TicketService.assign_ticket
"""

import json
import logging
from collections import defaultdict
from typing import Any

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from src.config.settings import get_settings
from src.data.clients.auth_client import auth_client
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
                "user_id": str(a.user_id),
                "display_name": a.display_name,
                "max_open_tickets": a.max_open_tickets,
                "customer_tier_id": a.customer_tier_id,
                "is_available": a.is_available,
            }
            for a in agents
        ]
    })


@tool
async def get_agent_resolution_history(agent_user_ids_json: str = "[]") -> str:
    """
    Retrieve the resolution history for the given agents.

    Input: A JSON array of agent user_id values, e.g. '["1", "2", "3"]'.
           If empty or "[]", returns an empty result.

    Returns a JSON object keyed by agent user_id, where each value contains:
      - total_resolved: number of tickets the agent resolved
      - by_product: dict mapping product name → count
      - by_area_of_concern: dict mapping area_of_concern → count
      - by_severity: dict mapping severity → count
      - by_priority: dict mapping priority → count

    Use this data to match agents with tickets they have the most experience in.
    """
    try:
        agent_ids = json.loads(agent_user_ids_json)
        if not isinstance(agent_ids, list):
            agent_ids = []
        agent_ids = [str(aid) for aid in agent_ids]
    except (json.JSONDecodeError, TypeError):
        agent_ids = []

    if not agent_ids:
        return json.dumps({"history": {}, "message": "No agent IDs provided."})

    async with AsyncSessionFactory() as session:
        ticket_repo = TicketRepository(session)
        resolved_tickets = await ticket_repo.get_resolved_by_assignees(agent_ids)

    # Build per-agent summary
    history: dict[str, dict[str, Any]] = {}
    for aid in agent_ids:
        history[aid] = {
            "total_resolved": 0,
            "by_product": defaultdict(int),
            "by_area_of_concern": defaultdict(int),
            "by_severity": defaultdict(int),
            "by_priority": defaultdict(int),
        }

    for t in resolved_tickets:
        aid = str(t.assignee_id)
        if aid not in history:
            continue
        h = history[aid]
        h["total_resolved"] += 1
        h["by_product"][t.product] += 1
        if t.area_of_concern:
            h["by_area_of_concern"][t.area_of_concern] += 1
        h["by_severity"][t.severity.value] += 1
        h["by_priority"][t.priority.value] += 1

    # Convert defaultdicts to plain dicts for JSON serialisation
    for aid in history:
        for key in ("by_product", "by_area_of_concern", "by_severity", "by_priority"):
            history[aid][key] = dict(history[aid][key])

    return json.dumps({"history": history})


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
        svc = TicketService(db=session, auth_client=auth_client)

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
