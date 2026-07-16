"""
Booking Agent — Appointment Scheduling.

Runs as a ReAct agent using create_react_agent. Handles all scheduling actions:
checking availability, reserving, cancelling, and rescheduling appointments.

This node always runs AFTER the Reception node, which guarantees that
contact_id is available in state.

Tools available:
  - check_availability_tool: query available slots by specialty/date
  - reserve_slot_tool: create a reservation for a slot
  - cancel_appointment_tool: cancel an existing reservation
  - reschedule_appointment_tool: move an appointment to a new slot
  - update_lead_tool: record lead qualification data after interaction
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langgraph.prebuilt import create_react_agent

from app.agents.llm_factory import get_llm
from app.agents.state import AgentState
from app.agents.utils import extract_text_content
from app.prompts import (
    GLOBAL_PROMPT,
    BOOKING_PROMPT,
    get_prompt_variables,
    render_prompt,
)
from app.tools.appointment_tools import (
    cancel_appointment_tool,
    cancel_reservation_tool,
    check_availability_tool,
    reschedule_appointment_tool,
    reserve_slot_tool,
)
from app.tools.qualification_tools import update_lead_tool

logger = logging.getLogger(__name__)

# Lazy-initialized ReAct agent — built on first call to avoid import-time LLM errors
_booking_react_agent = None


def _get_booking_agent():
    """Returns the booking ReAct agent, building it on first call."""
    global _booking_react_agent
    if _booking_react_agent is None:
        raw_prompt = GLOBAL_PROMPT + "\n\n" + BOOKING_PROMPT
        final_prompt = render_prompt(raw_prompt, **get_prompt_variables())
        _booking_react_agent = create_react_agent(
            model=get_llm(temperature=0.0),
            tools=[
                check_availability_tool,
                reserve_slot_tool,
                cancel_reservation_tool,   # for pre-payment reservation cancellations
                cancel_appointment_tool,   # for post-payment appointment cancellations
                reschedule_appointment_tool,
                update_lead_tool,
            ],
            prompt=final_prompt,
        )
    return _booking_react_agent


def booking_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: runs the Booking ReAct agent.

    Injects contextual information (contact_id, patient_id, conversation_id)
    into the message history so the LLM has full context without needing to
    ask for information already known.

    Returns:
        Partial state update with new messages, and optionally active_reservation_id.
    """
    logger.info(
        f"[Booking] Starting scheduling flow. "
        f"contact_id={state.get('contact_id')!r}, patient_id={state.get('patient_id')!r}"
    )

    # Inject a context message so the LLM knows who it's dealing with
    context_note = _build_context_note(state)
    messages = list(state["messages"])

    if context_note:
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=context_note)] + messages

    result = _get_booking_agent().invoke(
        {"messages": messages},
        config={"configurable": {"thread_id": state["conversation_id"]}},
    )

    new_messages = result.get("messages", [])

    # Attempt to extract active_reservation_id from tool outputs
    reservation_id = state.get("active_reservation_id")
    for msg in new_messages:
        content = extract_text_content(msg)
        if content:
            extracted = _extract_reservation_id(content)
            if extracted and not reservation_id:
                reservation_id = extracted
                logger.info(f"[Booking] Extracted reservation_id: {reservation_id}")

    logger.info("[Booking] Scheduling flow complete.")

    updates: dict[str, Any] = {"messages": new_messages}
    if reservation_id:
        updates["active_reservation_id"] = reservation_id
        # MOCK LOGIC for Milestone 6: If a reservation was just made, show payment buttons
        # In later milestones, this will be handled by the backend state properly.
        updates["ui_show_confirm_payment"] = True
        updates["ui_show_expire_payment"] = True
        updates["ui_payment_url"] = f"https://mock-payment-gateway.com/pay/{reservation_id}"

        logger.info("[Booking] Set mock UI payment flags.")

    # MOCK LOGIC: clear flags if we see a system message simulating payment confirm/expire
    for msg in messages:
        content = extract_text_content(msg)
        if content.startswith("[System Event: Payment"):
            updates["ui_show_confirm_payment"] = False
            updates["ui_show_expire_payment"] = False
            updates["ui_payment_url"] = None

    return updates


def _build_context_note(state: AgentState) -> str | None:
    """
    Builds a system-level context injection for the booking agent.
    Provides known state (contact_id, patient_id, conversation_id) so
    the agent doesn't re-ask for information already captured by reception.
    """
    parts: list[str] = []

    if state.get("contact_id"):
        parts.append(f"Contact ID: {state['contact_id']}")
    if state.get("patient_id"):
        parts.append(f"Patient ID: {state['patient_id']}")
    if state.get("conversation_id"):
        parts.append(f"Conversation ID: {state['conversation_id']}")
    if state.get("active_reservation_id"):
        parts.append(f"Active Reservation ID: {state['active_reservation_id']}")

    if not parts:
        return None

    return (
        "CONTEXT (provided by the Reception team — do not ask the user for this again):\n"
        + "\n".join(f"  - {p}" for p in parts)
    )


def _extract_reservation_id(text: str) -> str | None:
    """
    Attempt to extract a reservation_id from tool output text.
    """
    match = re.search(r'[\'"]reservation_id[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]', text)
    if match:
        return match.group(1)
    return None
