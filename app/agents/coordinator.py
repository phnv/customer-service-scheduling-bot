"""
Coordinator Node — Intent Classification & Routing.

This node receives the user's message, makes a single LLM call to classify
the intent, and writes the result to `state["intent"]`. The main graph then
uses conditional edges to route to the appropriate sub-graph.

The coordinator performs NO business logic — it only classifies and routes.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import SystemMessage

from app.agents.llm_factory import get_llm
from app.agents.state import AgentState
from app.agents.utils import extract_text_content
from app.prompts import (
    GLOBAL_PROMPT,
    COORDINATOR_PROMPT,
    get_prompt_variables,
    render_prompt,
)

logger = logging.getLogger(__name__)


def coordinator_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: classifies the user's latest message and sets state["intent"].

    Injects the current active conversation mode into the prompt so the LLM
    can make context-aware routing decisions (e.g., resume mid-booking flow).

    Returns:
        Partial state update — only sets `intent`. Messages are not modified here.
    """
    logger.info("[Coordinator] Classifying intent...")

    llm = get_llm(temperature=0.0)

    # Build prompt variables, injecting the active conversation mode context
    prompt_vars = get_prompt_variables()
    prompt_vars["ACTIVE_MODE_CONTEXT"] = _build_active_mode_context(state)

    raw_prompt = GLOBAL_PROMPT + "\n\n" + COORDINATOR_PROMPT
    final_prompt = render_prompt(raw_prompt, **prompt_vars)
    messages = [SystemMessage(content=final_prompt)] + list(state["messages"])

    response = llm.invoke(messages)
    raw_content = extract_text_content(response).strip()

    logger.info(f"[Coordinator] LLM raw response: {raw_content!r}")

    # Parse the JSON routing decision
    intent = _parse_intent(raw_content)
    logger.info(f"[Coordinator] Resolved intent: {intent!r}")

    return {"intent": intent}


def _build_active_mode_context(state: AgentState) -> str:
    """
    Returns a human-readable string describing the current active conversation
    mode so the coordinator LLM can make smarter routing decisions mid-flow.

    Example output:
        "The user is currently in an active 'booking' conversation. If the
        user's message is a direct answer to a previous question in that flow,
        prefer routing to 'booking' over switching intents."
    """
    active_intent = state.get("intent")
    if not active_intent or active_intent not in {"booking", "faq"}:
        return "There is no active conversation mode. Classify intent from scratch."

    return (
        f"The user is currently in an active '{active_intent}' conversation. "
        f"If the user's message is a direct continuation or answer to a previous question "
        f"in that flow, prefer routing to '{active_intent}' over switching intents."
    )


def _parse_intent(raw: str) -> str:
    """
    Safely parse the JSON intent response from the coordinator LLM.

    Falls back to "escalation" if the response is malformed — better to
    escalate than to route incorrectly.
    """
    valid_intents = {"booking", "faq", "escalation"}

    try:
        # Strip markdown code fences if the model wrapped the JSON
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(cleaned)
        intent = str(data.get("intent", "")).lower().strip()

        if intent in valid_intents:
            return intent

        logger.warning(
            f"[Coordinator] Unexpected intent value: {intent!r}. Falling back to 'escalation'."
        )
        return "escalation"

    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"[Coordinator] Failed to parse intent JSON: {e}. Falling back to 'escalation'.")
        return "escalation"


def route_after_coordinator(state: AgentState) -> str:
    """
    Conditional edge function: maps state["intent"] to the next node name.

    Used by the main graph's add_conditional_edges call.
    """
    intent = state.get("intent", "escalation")

    routing_map = {
        "booking": "reception",
        "faq": "faq",
        "escalation": "escalation",
    }

    next_node = routing_map.get(intent, "escalation")
    logger.info(f"[Coordinator] Routing to: {next_node!r} (intent={intent!r})")
    return next_node
