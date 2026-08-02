"""
FAQ Agent — General Knowledge Questions.

Runs as a ReAct agent using create_react_agent. Answers general questions
about the clinic by querying the knowledge base via search_faq_tool.

Tools available:
  - search_faq_tool: query the clinic knowledge base via semantic search
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from app.agents.llm_factory import get_llm
from app.agents.state import AgentState
from app.prompts import (
    GLOBAL_PROMPT,
    FAQ_PROMPT,
    get_prompt_variables,
    render_prompt,
)
from app.tools.faq_tools import search_faq_tool

logger = logging.getLogger(__name__)

# Lazy-initialized ReAct agent — built on first call to avoid import-time LLM errors
_faq_react_agent = None


def _get_faq_agent():
    """Returns the FAQ ReAct agent, building it on first call."""
    global _faq_react_agent
    if _faq_react_agent is None:
        raw_prompt = GLOBAL_PROMPT + "\n\n" + FAQ_PROMPT
        final_prompt = render_prompt(raw_prompt, **get_prompt_variables())
        _faq_react_agent = create_react_agent(
            model=get_llm(),
            tools=[search_faq_tool],
            prompt=final_prompt,
        )
    return _faq_react_agent


def faq_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: runs the FAQ ReAct agent.

    Returns:
        Partial state update with new messages from the FAQ agent.
    """
    logger.info("[FAQ] Starting knowledge base lookup...")

    messages = list(state["messages"])
    context_note = _build_context_note(state)
    if context_note:
        messages = [SystemMessage(content=context_note)] + messages

    result = _get_faq_agent().invoke(
        {"messages": messages},
        config={"configurable": {"thread_id": state["conversation_id"]}},
    )

    new_messages = result.get("messages", [])
    logger.info("[FAQ] Knowledge base response complete.")

    return {"messages": new_messages}


def _build_context_note(state: AgentState) -> str | None:
    """
    Builds a system-level context injection for the FAQ agent.

    Currently only surfaces the rolling conversation_summary maintained by the
    Coordinator, so the FAQ agent has awareness of the broader conversation
    (e.g., an in-progress booking) even though it has no scheduling tools.
    """
    if state.get("conversation_summary"):
        return f"Conversation Summary: {state['conversation_summary']}"
    return None
