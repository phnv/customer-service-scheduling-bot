"""Smoke test for Milestone 5 agent imports and static logic."""
import logging
logging.basicConfig(level=logging.WARNING)

print("=== Test 1: Module imports ===")
from app.agents.state import AgentState
from app.agents.coordinator import coordinator_node, route_after_coordinator, _parse_intent
from app.agents.reception_agent import reception_node
from app.agents.booking_agent import booking_node
from app.agents.faq_agent import faq_node
from app.agents.graph import run_agent, _graph
from app.tools.faq_tools import search_faq_tool
from app.prompts.prompts import (
    COORDINATOR_PROMPT, RECEPTION_PROMPT, BOOKING_PROMPT,
    FAQ_PROMPT, ESCALATION_MESSAGE
)
print("All modules imported successfully.")

print()
print("=== Test 2: Graph compiled ===")
print(f"Graph type: {type(_graph).__name__}")

print()
print("=== Test 3: FAQ stub tool ===")
result = search_faq_tool.invoke({"query": "what are your opening hours"})
print(f"hours query: {result[:80]}...")

result2 = search_faq_tool.invoke({"query": "what is the cancellation policy"})
print(f"cancel query: {result2[:80]}...")

result3 = search_faq_tool.invoke({"query": "something completely unknown"})
print(f"unknown query: {result3[:80]}...")

print()
print("=== Test 4: Intent parser ===")
assert _parse_intent('{"intent": "booking"}') == "booking", "booking failed"
assert _parse_intent('{"intent": "faq"}') == "faq", "faq failed"
assert _parse_intent('{"intent": "escalation"}') == "escalation", "escalation failed"
assert _parse_intent("BROKEN JSON {{") == "escalation", "malformed fallback failed"
assert _parse_intent('{"intent": "unknown_value"}') == "escalation", "unknown intent fallback failed"
assert _parse_intent('```json\n{"intent": "booking"}\n```') == "booking", "markdown-wrapped failed"
print("Intent parser: all 6 assertions passed.")

print()
print("=== Test 5: Prompts non-empty ===")
assert len(COORDINATOR_PROMPT) > 100, "coordinator prompt too short"
assert len(RECEPTION_PROMPT) > 100, "reception prompt too short"
assert len(BOOKING_PROMPT) > 100, "booking prompt too short"
assert len(FAQ_PROMPT) > 100, "faq prompt too short"
assert len(ESCALATION_MESSAGE) > 20, "escalation message too short"
print("All prompts are non-empty and reasonable length.")

print()
print("=== All static checks PASSED ===")
