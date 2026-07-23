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

    llm = get_llm(temperature=0.0)

    # Build prompt variables, injecting the active flow + summary context
    prompt_vars = get_prompt_variables()
    prompt_vars["ACTIVE_MODE_CONTEXT"] = _build_active_mode_context(state)

    raw_prompt = GLOBAL_PROMPT + "\n\n" + COORDINATOR_PROMPT
    final_prompt = render_prompt(raw_prompt, **prompt_vars)
    messages = [SystemMessage(content=final_prompt)] + list(state["messages"])

    response = llm.invoke(messages)
    raw_content = extract_text_content(response).strip()

    logger.info(f"[Coordinator] LLM raw response: {raw_content!r}")

    intent, flow, conversation_summary_update = _parse_coordinator_response(
        raw_content, current_flow=state.get("flow")
    )
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


def _parse_coordinator_response(
    raw: str, current_flow: Optional[str]
) -> tuple[str, Optional[str], Optional[str]]:
    """
    Parses the coordinator LLM's JSON response into (intent, flow, conversation_summary_update).

    - intent: always resolved to a valid value ("booking" | "faq" | "escalation"),
      falling back to "escalation" on any parse failure or invalid value.
    - flow: resolved from the response's "flow" key. If the key is missing or its
      value is invalid, the previous `current_flow` is preserved unchanged. An
      explicit JSON `null` clears it. Valid values: "booking" | "faq" | None.
    - conversation_summary_update: the new summary paragraph if the LLM decided to
      rewrite it (a non-empty string), or None if it should be left unchanged
      (the LLM returned null/omitted the key, or parsing failed). Callers must
      treat None as "no update" and OMIT conversation_summary from the returned
      state dict entirely — never overwrite the existing summary with None.
    """
    valid_intents = {"booking", "faq", "escalation"}
    valid_flows = {"booking", "faq"}

    try:
        # Strip markdown code fences if the model wrapped the JSON
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"[Coordinator] Failed to parse JSON response: {e}. Falling back to 'escalation'.")
        return "escalation", current_flow, None

    # --- intent (required, always resolved) ---
    intent = str(data.get("intent", "")).lower().strip()
    if intent not in valid_intents:
        logger.warning(
            f"[Coordinator] Unexpected intent value: {intent!r}. Falling back to 'escalation'."
        )
        intent = "escalation"

    # --- flow (optional; missing/invalid preserves current value) ---
    if "flow" not in data:
        flow = current_flow
    else:
        raw_flow = data["flow"]
        if raw_flow is None:
            flow = None
        else:
            candidate = str(raw_flow).lower().strip()
            flow = candidate if candidate in valid_flows else current_flow

    # --- conversation_summary (optional; missing/null/empty means "no update") ---
    raw_summary = data.get("conversation_summary")
    if isinstance(raw_summary, str) and raw_summary.strip():
        conversation_summary_update = raw_summary.strip()
    else:
        conversation_summary_update = None

    return intent, flow, conversation_summary_update


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

