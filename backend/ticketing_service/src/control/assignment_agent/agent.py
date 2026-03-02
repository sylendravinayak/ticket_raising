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
from src.control.assignment_agent.tools import get_available_agents, assign_ticket_to_agent

logger = logging.getLogger(__name__)
settings = get_settings()

def build_assignment_agent():
    """
    Build and return the LangGraph ReAct agent.
    Reuse this instance — it is stateless between invocations.
    """
    llm = ChatGroq(
        model="llama3-70b-8192",          # or "mixtral-8x7b-32768"
        api_key=settings.groq_api_key,
        temperature=0,
    )

    agent = create_react_agent(
        model=llm,
        tools=[get_available_agents, assign_ticket_to_agent],
    )
    return agent


_agent = None


def get_assignment_agent():
    global _agent
    if _agent is None:
        _agent = build_assignment_agent()
    return _agent
