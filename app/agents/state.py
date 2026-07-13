"""
Shared state schema for the multi-agent LangGraph graph.

All agents and nodes read from and write to this state object.
The `messages` field uses LangGraph's `add_messages` reducer so that
new messages are appended (not replaced) on each graph invocation.
"""

from __future__ import annotations

from typing import Annotated, Optional
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Typed state shared across all nodes in the conversation graph."""

    # Full conversation history — appended via add_messages reducer
    messages: Annotated[list[BaseMessage], add_messages]

    # Stable identifier for the ongoing conversation (maps to DB conversations.conversation_id)
    conversation_id: str

    # Populated by the Reception agent after identifying/creating the contact
    contact_id: Optional[str]

    # Populated after the user selects which patient this booking is for
    patient_id: Optional[str]

    # Set when an active reservation has been created in the current conversation
    active_reservation_id: Optional[str]

    # Set by the Coordinator node — drives conditional routing
    # Values: "booking" | "faq" | "escalation"
    intent: Optional[str]

    # Populated by the FAQ Agent's RAG tool to pass context to the UI
    retrieved_docs: Optional[list[dict]]

    # --- UI Demo Flags ---
    ui_payment_url: Optional[str]
    ui_show_confirm_payment: bool
    ui_show_expire_payment: bool

