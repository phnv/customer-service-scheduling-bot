"""
Generalistic agent smoke tests.

Purpose
-------
Assert that each agent node (coordinator → escalation | faq | booking)
can be invoked end-to-end without raising any exception and returns at least
one non-empty AI text response.

These tests are *structural* crash guards — they catch the class of bug where
a node raises an unhandled exception (e.g. TypeError from a bad render_prompt
call) before it can return any response.  They are intentionally kept narrow:
no semantic assertions about response quality, tone, or correctness.

Test-first discipline
---------------------
``test_should_return_response_when_intent_is_escalation`` was written BEFORE
the fix for the TypeError in escalation_agent.py.  It fails on the unfixed
agent and goes green once the fix is applied.  The other two tests serve as
regression guards for nodes that were already working.

Design note: plain pytest (no @mlflow.test / mlflow.genai.evaluate)
-----------------------------------------------------------------------
These are structural crash guards, not semantic quality assertions.  The
failure mode being tested is an unhandled exception — a TypeError, not a
bad answer.  mlflow.genai.evaluate / @mlflow.test add infrastructure
(run creation, scorer dispatch, LLM judge calls) that is the right tool for
semantic quality checks but conflicts with graph.py's module-level
load_dotenv() + mlflow.langchain.autolog() when running under the mlflow
pytest plugin.  Plain pytest with a direct call to run_agent() is the
correct, minimal tool for this class of assertion.

MLflow tracing
--------------
mlflow.langchain.autolog() is activated at app/agents/graph.py module load
— the same path production uses.  Tests do NOT re-declare tracing so the
instrumentation stays identical to prod (per fix-agent-issue SKILL.md §
"Exercise the real instrumented code path").
"""

from __future__ import annotations

import pytest


def _invoke(user_message: str, conversation_id: str) -> str:
    """
    Call run_agent through the production entry point.

    Late import ensures graph.py's load_dotenv() + mlflow.langchain.autolog()
    run exactly once, in the same order as production, not in test setup.
    """
    from app.agents.graph import run_agent
    response, _state = run_agent(
        user_message=user_message,
        conversation_id=conversation_id,
    )
    return response


# ---------------------------------------------------------------------------
# Smoke tests — one per agent intent path.
# ---------------------------------------------------------------------------

def test_should_return_response_when_intent_is_escalation():
    """
    The escalation node must return a non-empty response when the user expresses
    a desire to speak with a human.

    This test was RED before the fix for:
        TypeError: render_prompt() takes 1 positional argument but 2 were given
        (escalation_agent.py line 29)
    """
    response = _invoke(
        user_message="I am very frustrated and I want to speak to a real person right now.",
        conversation_id="smoke-test-escalation-001",
    )
    assert isinstance(response, str) and response.strip(), (
        "Escalation node returned an empty or non-string response"
    )


def test_should_return_response_when_intent_is_faq():
    """
    The FAQ node must return a non-empty response for a general information query.
    """
    response = _invoke(
        user_message="What are your clinic's opening hours?",
        conversation_id="smoke-test-faq-001",
    )
    assert isinstance(response, str) and response.strip(), (
        "FAQ node returned an empty or non-string response"
    )


def test_should_return_response_when_intent_is_booking():
    """
    The booking pipeline must return a non-empty response for an appointment
    booking request (coordinator → reception or booking node).
    """
    response = _invoke(
        user_message="I need to book an appointment with a cardiologist.",
        conversation_id="smoke-test-booking-001",
    )
    assert isinstance(response, str) and response.strip(), (
        "Booking node returned an empty or non-string response"
    )
