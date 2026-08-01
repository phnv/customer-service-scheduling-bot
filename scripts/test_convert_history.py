"""Smoke test for _convert_history() — run from project root with uv run python."""
import sys
from pathlib import Path

# Ensure project root is on path (same pattern as run_evaluation.py)
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.graph import _convert_history
from langchain_core.messages import HumanMessage, AIMessage

# Test 1: normal history converts correctly
h = _convert_history([
    {"role": "user", "content": "Hi, my phone is +15550001234."},
    {"role": "assistant", "content": "Welcome back, John!"},
])
assert isinstance(h[0], HumanMessage), f"Expected HumanMessage, got {type(h[0])}"
assert isinstance(h[1], AIMessage),    f"Expected AIMessage, got {type(h[1])}"
assert h[0].content == "Hi, my phone is +15550001234."
assert h[1].content == "Welcome back, John!"
print("PASS — normal history converts correctly")

# Test 2: empty list returns empty list
assert _convert_history([]) == []
print("PASS — empty history returns []")

# Test 3: unknown role raises ValueError
try:
    _convert_history([{"role": "system", "content": "bad"}])
    print("FAIL — should have raised ValueError")
except ValueError as e:
    print(f"PASS — strict mapping raises ValueError: {e}")

print("\nAll smoke tests passed.")
