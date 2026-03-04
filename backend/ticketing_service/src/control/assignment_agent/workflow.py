import json
import logging
from typing import Any
from src.config.settings import get_settings
from src.control.assignment_agent.agent import get_assignment_agent


logger = logging.getLogger(__name__)
settings = get_settings()

async def run_auto_assign(
    ticket_id: int,
    ticket_title: str,
    ticket_priority: str,
    assigner_id: str,
    assigner_role: str,
) -> dict[str, Any]:
    """
    Ask the AI agent to automatically pick the best available agent
    and assign the given ticket. Returns the final agent response dict.

    Usage:
        result = await run_auto_assign(
            ticket_id=42,
            ticket_title="Login page crashes on Safari",
            ticket_priority="P1",
            assigner_id="<team-lead-uuid>",
            assigner_role="team_lead",
        )
    """
    agent = get_assignment_agent()

    prompt = (
        f"You are a ticket routing assistant.\n"
        f"Ticket ID   : {ticket_id}\n"
        f"Ticket Title: {ticket_title}\n"
        f"Priority    : {ticket_priority}\n\n"
        f"Steps:\n"
        f"1. Call `get_available_agents` to list all available support agents.\n"
        f"2. Call `get_agent_resolution_history` with the user_ids from step 1 "
        f"   to see what kinds of tickets each agent has resolved before.\n"
        f"3. Pick the most suitable available agent by considering:\n"
        f"   - Agent's past experience with similar products/areas/severities\n"
        f"   - Agents with lower current load / matching tier\n"
        f"   - Agents who have resolved similar tickets before should be preferred\n"
        f"4. Call `assign_ticket_to_agent` with the ticket and chosen agent details:\n"
        f"   assigner_id={assigner_id}, assigner_role={assigner_role}\n"
        f"5. Report the final assignment result clearly, including why the agent was chosen."
        f"6.If any error print the error details."
    )

    result = await agent.ainvoke({"messages": [{"content": prompt, "role": "user"}]})

    last_message = result["messages"][-1]
    logger.info("Assignment agent result for ticket %s: %s", ticket_id, last_message.content)

    return {
        "ticket_id": ticket_id,
        "agent_response": last_message.content,
        "full_messages": [m.content for m in result["messages"]],
    }