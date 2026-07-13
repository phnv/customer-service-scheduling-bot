"""
Main LangGraph graph — Multi-Agent Customer Service Pipeline.

Architecture: Supervisor pattern
  START → [coordinator] → routes to → [reception] → [booking]
                                   → [faq]
                                   → [escalation]
  Each terminal node → END

Persistence: MemorySaver in-process checkpointer.
  - thread_id = conversation_id enables multi-turn memory within a session.
  - State is lost on process restart (acceptable for a portfolio project).

Public API:
  run_agent(user_message: str, conversation_id: str) -> tuple[str, dict[str, Any]]
    Called by the Streamlit UI on each user message.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.booking_agent import booking_node
from app.agents.coordinator import coordinator_node, route_after_coordinator
from app.agents.faq_agent import faq_node
from app.agents.reception_agent import reception_node
from app.agents.state import AgentState
from app.agents.utils import extract_text_content
from app.prompts import ESCALATION_MESSAGE

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Escalation Node (static gateway — not a ReAct agent)
# ---------------------------------------------------------------------------

def escalation_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: returns a static escalation message.

    Per architecture decision: escalation is a gateway node, not an agent.
    It does not call any LLM or tools.
    """
    logger.info("[Escalation] Routing to human escalation.")
    return {
        "messages": [AIMessage(content=ESCALATION_MESSAGE)]
    }


# ---------------------------------------------------------------------------
# Graph Assembly
# ---------------------------------------------------------------------------

def _build_graph() -> Any:
    """Assembles and compiles the main StateGraph with MemorySaver checkpointer."""

    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("reception", reception_node)
    graph.add_node("booking", booking_node)
    graph.add_node("faq", faq_node)
    graph.add_node("escalation", escalation_node)

    # Entry point
    graph.add_edge(START, "coordinator")

    # Coordinator → conditional routing based on intent
    graph.add_conditional_edges(
        "coordinator",
        route_after_coordinator,
        {
            "reception": "reception",   # booking flow: always pass through reception
            "faq": "faq",
            "escalation": "escalation",
        },
    )

    # Reception always hands off to Booking
    graph.add_edge("reception", "booking")

    # Terminal edges
    graph.add_edge("booking", END)
    graph.add_edge("faq", END)
    graph.add_edge("escalation", END)

    # Compile with in-memory checkpointer for multi-turn persistence
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# Singleton compiled graph — built once, reused across all run_agent calls
_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_agent(user_message: str, conversation_id: str | None = None) -> tuple[str, dict[str, Any]]:
    """
    Process a user message through the multi-agent pipeline and return the response and state.

    This is the single entry point called by the Streamlit UI (via ChatApplication).

    Args:
        user_message: The raw text sent by the user.
        conversation_id: Stable ID linking this message to a conversation session.
                         If None, a new UUID is generated (single-turn usage).

    Returns:
        A tuple of (agent_response_string, final_agent_state_dict).
    """
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        logger.warning(
            f"[Graph] No conversation_id provided — generated ephemeral ID: {conversation_id}"
        )

    logger.info(
        f"[Graph] run_agent called. conversation_id={conversation_id!r}, "
        f"message={user_message[:80]!r}{'...' if len(user_message) > 80 else ''}"
    )

    # LangGraph config: thread_id enables MemorySaver to restore prior state
    config = {"configurable": {"thread_id": conversation_id}}

    initial_state: dict[str, Any] = {
        "messages": [HumanMessage(content=user_message)],
        "conversation_id": conversation_id,
    }

    result = _graph.invoke(initial_state, config=config)

    # Extract the last AI message as the response
    response = _extract_last_ai_message(result)
    logger.info(f"[Graph] Response: {response[:120]!r}{'...' if len(response) > 120 else ''}")

    return response, result


def _extract_last_ai_message(state: dict[str, Any]) -> str:
    """
    Extracts the content of the last AIMessage from the final graph state.

    Falls back to a generic error message if no AI response is found.
    """
    messages = state.get("messages", [])

    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = extract_text_content(msg)
            if content:
                return content

    logger.error("[Graph] No AIMessage found in final state — returning fallback response.")
    return (
        "I'm sorry, I encountered an issue processing your request. "
        "Please try again or contact our reception directly."
    )
