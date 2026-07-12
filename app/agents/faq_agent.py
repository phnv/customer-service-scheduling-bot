"""
FAQ Agent — General Knowledge Questions.

Runs as a ReAct agent using create_react_agent. Answers general questions
about the clinic by querying the knowledge base via search_faq_tool.

Note: In Milestone 5, search_faq_tool is a keyword-matching stub.
      A full semantic RAG pipeline will replace it in Milestone 6.

Tools available:
  - search_faq_tool: keyword-matched stub knowledge base lookup
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.prebuilt import create_react_agent

from app.agents.llm_factory import get_llm
from app.agents.state import AgentState
from app.prompts.prompts import FAQ_PROMPT
from app.tools.faq_tools import search_faq_tool

logger = logging.getLogger(__name__)

# Lazy-initialized ReAct agent — built on first call to avoid import-time LLM errors
_faq_react_agent = None


def _get_faq_agent():
    """Returns the FAQ ReAct agent, building it on first call."""
    global _faq_react_agent
    if _faq_react_agent is None:
        _faq_react_agent = create_react_agent(
            model=get_llm(temperature=0.0),
            tools=[search_faq_tool],
            prompt=FAQ_PROMPT,
        )
    return _faq_react_agent


def faq_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: runs the FAQ ReAct agent.

    Returns:
        Partial state update with new messages from the FAQ agent.
    """
    logger.info("[FAQ] Starting knowledge base lookup...")

    result = _get_faq_agent().invoke(
        {"messages": list(state["messages"])},
        config={"configurable": {"thread_id": state["conversation_id"]}},
    )

    new_messages = result.get("messages", [])
    logger.info("[FAQ] Knowledge base response complete.")

    return {"messages": new_messages}
