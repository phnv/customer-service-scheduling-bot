"""
Reception Agent — Contact Identification & Patient Selection.

Runs as a ReAct agent using create_react_agent. It always executes before
the Booking agent to ensure we have a valid contact_id and patient_id in state.


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
from app.prompts import (
    GLOBAL_PROMPT,
    RECEPTION_PROMPT,
    get_prompt_variables,
    render_prompt,
)
from app.tools.customer_tools import (
    find_contact_tool,
    create_contact_tool,
    update_contact_tool,
    find_patient_tool,
    create_patient_tool,
    select_patient_tool,
)

logger = logging.getLogger(__name__)

# Lazy-initialized ReAct agent — built on first call to avoid import-time LLM errors
_reception_react_agent = None


def _get_reception_agent():
    """Returns the reception ReAct agent, building it on first call."""
    global _reception_react_agent
    if _reception_react_agent is None:
        raw_prompt = GLOBAL_PROMPT + "\n\n" + RECEPTION_PROMPT
        final_prompt = render_prompt(raw_prompt, **get_prompt_variables())
        _reception_react_agent = create_react_agent(
            model=get_llm(temperature=0.0),
            tools=[
                find_contact_tool,
                create_contact_tool,
                update_contact_tool,
                find_patient_tool,
                create_patient_tool,
                select_patient_tool,
            ],
            prompt=final_prompt,
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

    messages = list(state["messages"])
    context_note = _build_context_note(state)
    if context_note:
        messages = [SystemMessage(content=context_note)] + messages

    # Invoke the ReAct agent with current message history
    result = _get_reception_agent().invoke(
        {"messages": messages},
        config={"configurable": {"thread_id": state["conversation_id"]}},
    )

    new_messages = result.get("messages", [])

    # Try to extract contact_id from tool call results in the message trace
    contact_id = state.get("contact_id")
    patient_id = state.get("patient_id")

    for msg in new_messages:
        content = extract_text_content(msg)
        if content:
            extracted_contact = _extract_contact_id(content)
            if extracted_contact and not contact_id:
                contact_id = extracted_contact
                logger.info(f"[Reception] Extracted contact_id: {contact_id}")

            extracted_patient = _extract_patient_id(content)
            if extracted_patient and not patient_id:
                patient_id = extracted_patient
                logger.info(f"[Reception] Extracted patient_id: {patient_id}")

    logger.info(
        f"[Reception] Done. contact_id={contact_id!r}, patient_id={patient_id!r}"
    )

    updates: dict[str, Any] = {"messages": new_messages}
    if contact_id:
        updates["contact_id"] = contact_id
    if patient_id:
        updates["patient_id"] = patient_id

    return updates


def _build_context_note(state: AgentState) -> str | None:
    """
    Builds a system-level context injection for the reception agent.

    Currently only surfaces the rolling conversation_summary maintained by the
    Coordinator (booking/patient identity injection is not needed here since
    Reception is responsible for establishing those IDs itself).
    """
    if state.get("conversation_summary"):
        return f"Conversation Summary: {state['conversation_summary']}"
    return None


def _extract_contact_id(text: str) -> str | None:
    """
    Attempt to extract a contact_id from tool output text.
    """
    match = re.search(r'[\'"]contact_id[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]', text)
    if match:
        return match.group(1)
    return None

def _extract_patient_id(text: str) -> str | None:
    """
    Attempt to extract a patient_id from tool output text.
    """
    match = re.search(r'[\'"]selected_patient_id[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]', text)
    if match:
        return match.group(1)
    return None
