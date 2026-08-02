"""
Coordinator Node — Intent Classification & Routing.

This node receives the user's message, makes a single LLM call to classify
the intent, and writes the result to `state["intent"]`. The main graph then
uses conditional edges to route to the appropriate sub-graph.

In addition to `intent` (the routing decision for THIS turn only), the
coordinator also maintains two longer-lived state fields:
  - `flow`: the durable multi-turn task the user is engaged in ("booking" |
    "faq" | None). Unlike `intent`, this persists across single-turn detours
    (e.g. one FAQ question asked mid-booking) and is only changed when the
    LLM judges the user has switched, resumed, or abandoned a durable task.
  - `conversation_summary`: a single-paragraph rolling summary, rewritten
    only when the LLM judges something meaningful happened. Left unchanged
    (never wiped) on quiet turns.

The coordinator performs NO business logic — it only classifies and routes.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from app.agents.llm_factory import get_llm
from app.agents.state import AgentState
from app.prompts import (
    GLOBAL_PROMPT,
    COORDINATOR_PROMPT,
    get_prompt_variables,
    render_prompt,
)

logger = logging.getLogger(__name__)


class CoordinatorOutput(BaseModel):
    intent: str = Field(description="The routing decision for THIS turn only (booking, faq, escalation).")
    flow: Optional[str] = Field(None, description="The durable multi-turn task (booking, faq, or null).")
    conversation_summary: Optional[str] = Field(None, description="A single-paragraph rolling summary.")

def coordinator_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: classifies the user's latest message and sets
    state["intent"] and state["flow"], and optionally rewrites
    state["conversation_summary"].

    Injects the current active flow (and summary) into the prompt so the LLM
    can make context-aware routing decisions (e.g., resume mid-booking flow).

    Returns:
        Partial state update — sets `intent` and `flow` on every call;
        `conversation_summary` is only included when the LLM decided to
        rewrite it, so it is never wiped on a quiet turn.
    """
    logger.info("[Coordinator] Classifying intent...")

    llm = get_llm()
    structured_llm = llm.with_structured_output(CoordinatorOutput)

    # Build prompt variables, injecting the active flow + summary context
    prompt_vars = get_prompt_variables()
    prompt_vars["ACTIVE_MODE_CONTEXT"] = _build_active_mode_context(state)

    raw_prompt = GLOBAL_PROMPT + "\n\n" + COORDINATOR_PROMPT
    final_prompt = render_prompt(raw_prompt, **prompt_vars)
    messages = [SystemMessage(content=final_prompt)] + list(state["messages"])

    response = structured_llm.invoke(messages)

    intent = response.intent.lower().strip() if response.intent else "escalation"
    if intent not in {"booking", "faq", "escalation"}:
        intent = "escalation"

    flow = response.flow.lower().strip() if response.flow else None
    if flow not in {"booking", "faq"}:
        flow = state.get("flow")

    conversation_summary_update = response.conversation_summary.strip() if response.conversation_summary and response.conversation_summary.strip() else None

    logger.info(f"[Coordinator] Resolved intent={intent!r}, flow={flow!r}")

    updates: dict[str, Any] = {"intent": intent, "flow": flow}
    if conversation_summary_update is not None:
        updates["conversation_summary"] = conversation_summary_update
        logger.info(f"[Coordinator] Updated conversation_summary: {conversation_summary_update!r}")

    return updates


def _build_active_mode_context(state: AgentState) -> str:
    """
    Returns a human-readable string describing the current active flow (and
    rolling summary, if any) so the coordinator LLM can make smarter routing
    decisions mid-conversation.
    """
    active_flow = state.get("flow")
    summary = state.get("conversation_summary")

    if not active_flow or active_flow not in {"booking", "faq"}:
        context = "There is no active conversation flow. Classify intent from scratch."
    else:
        context = (
            f"The user is currently engaged in an active '{active_flow}' flow. "
            f"If the user's message is a direct continuation or answer to a previous "
            f"question in that flow, prefer routing to '{active_flow}' over switching "
            f"intents. A single-turn detour (e.g. one FAQ question) does not end the "
            f"flow — keep 'flow' as '{active_flow}' unless the user clearly finishes, "
            f"abandons, or switches to a different durable task."
        )

    if summary:
        context += f"\n\nConversation summary so far: {summary}"

    return context





def route_after_coordinator(state: AgentState) -> str:
    """
    Conditional edge function: maps state["intent"] to the next node name.

    Routing keys off `intent` only (the per-turn routing decision), not
    `flow` (the durable-task tracker) — this is unchanged by the flow/summary
    feature.

    Used by the main graph's add_conditional_edges call.
    """
    intent = state.get("intent", "escalation")

    if intent == "booking":
        if state.get("contact_id") and state.get("patient_id"):
            next_node = "booking"
        else:
            next_node = "reception"
    else:
        next_node = intent

    logger.info(f"[Coordinator] Routing to: {next_node!r} (intent={intent!r})")
    return next_node

