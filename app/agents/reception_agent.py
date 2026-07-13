"""
Reception Agent — Contact Identification & Patient Selection.

Runs as a ReAct agent using create_react_agent. It always executes before
the Booking agent to ensure we have a valid contact_id and patient_id in state.

Tools available:
  - find_customer_tool: lookup contact by phone, document, or email
  - register_customer_tool: create a new contact if not found

After completing its work, this node also attempts to extract and persist
the contact_id into the shared AgentState for downstream agents.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from app.agents.llm_factory import get_llm
from app.agents.state import AgentState
from app.agents.utils import extract_text_content
from app.prompts.prompts import RECEPTION_PROMPT
from app.tools.customer_tools import find_customer_tool, register_customer_tool

logger = logging.getLogger(__name__)

# Lazy-initialized ReAct agent — built on first call to avoid import-time LLM errors
_reception_react_agent = None


def _get_reception_agent():
    """Returns the reception ReAct agent, building it on first call."""
    global _reception_react_agent
    if _reception_react_agent is None:
        _reception_react_agent = create_react_agent(
            model=get_llm(temperature=0.0),
            tools=[find_customer_tool, register_customer_tool],
            prompt=RECEPTION_PROMPT,
        )
    return _reception_react_agent


def reception_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: runs the Reception ReAct agent.

    The agent identifies or creates a contact, then confirms the patient.
    It updates state with contact_id and patient_id if extractable from
    tool outputs.

    Returns:
        Partial state update with new messages, and optionally contact_id/patient_id.
    """
    logger.info("[Reception] Starting contact identification...")

    # Invoke the ReAct agent with current message history
    result = _get_reception_agent().invoke(
        {"messages": list(state["messages"])},
        config={"configurable": {"thread_id": state["conversation_id"]}},
    )

    new_messages = result.get("messages", [])

    # Try to extract contact_id from tool call results in the message trace
    contact_id = state.get("contact_id")
    patient_id = state.get("patient_id")

    for msg in new_messages:
        content = extract_text_content(msg)
        if content:
            extracted = _extract_contact_id(content)
            if extracted and not contact_id:
                contact_id = extracted
                logger.info(f"[Reception] Extracted contact_id: {contact_id}")

    logger.info(
        f"[Reception] Done. contact_id={contact_id!r}, patient_id={patient_id!r}"
    )

    updates: dict[str, Any] = {"messages": new_messages}
    if contact_id:
        updates["contact_id"] = contact_id
    if patient_id:
        updates["patient_id"] = patient_id

    return updates


def _extract_contact_id(text: str) -> str | None:
    """
    Attempt to extract a contact_id from tool output text.

    Tool outputs may contain a JSON snippet like {"contact_id": "abc-123"}.
    This is a best-effort parse; the LLM itself tracks this in conversation context.
    """
    match = re.search(r'"contact_id"\s*:\s*"([^"]+)"', text)
    if match:
        return match.group(1)
    return None
