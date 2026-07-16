from app.prompts import BOOKING_PROMPT, COORDINATOR_PROMPT, RECEPTION_PROMPT
from app.prompts import render_prompt, get_prompt_variables
from app.agents.coordinator import _build_active_mode_context

# Test render_prompt with all expected variables
vars = get_prompt_variables()
vars["ACTIVE_MODE_CONTEXT"] = "There is no active conversation mode."

rendered_coordinator = render_prompt(COORDINATOR_PROMPT, **vars)
rendered_booking = render_prompt(BOOKING_PROMPT, **vars)
rendered_reception = render_prompt(RECEPTION_PROMPT, **vars)

assert "{{" not in rendered_coordinator, "Unrendered placeholders in COORDINATOR_PROMPT"
assert "{{" not in rendered_booking, "Unrendered placeholders in BOOKING_PROMPT"
assert "{{" not in rendered_reception, "Unrendered placeholders in RECEPTION_PROMPT"

# Test _build_active_mode_context
state_no_intent = {}
state_booking = {"intent": "booking"}
state_faq = {"intent": "faq"}
state_escalation = {"intent": "escalation"}

r1 = _build_active_mode_context(state_no_intent)
r2 = _build_active_mode_context(state_booking)
r3 = _build_active_mode_context(state_faq)
r4 = _build_active_mode_context(state_escalation)

assert "no active" in r1
assert "booking" in r2
assert "faq" in r3
assert "no active" in r4  # escalation doesn't have a resumable mode

# Verify cancel_reservation_tool is importable
from app.tools.appointment_tools import cancel_reservation_tool
assert cancel_reservation_tool is not None

# Verify booking_agent imports cancel_reservation_tool in its tool list
import inspect
import app.agents.booking_agent as ba
src = inspect.getsource(ba._get_booking_agent)
assert "cancel_reservation_tool" in src
assert "cancel_appointment_tool" in src

print("ALL CHECKS PASSED")
