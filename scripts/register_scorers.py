"""
Register evaluation scorers for prompt evaluation.

Registers 5 scorers into the MLflow experiment:
  1. Routing Accuracy     — deterministic (custom Python scorer)
  2. Domain Containment   — LLM-as-judge via make_judge()
  3. Response Quality     — LLM-as-judge via make_judge()
  4. Tool Selection       — LLM-as-judge via make_judge()
  5. Hallucination Check  — LLM-as-judge via make_judge()

Usage:
    uv run python scripts/register_scorers.py
"""

import os
import sys
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

import mlflow
from mlflow.genai.judges import make_judge

# ---------------------------------------------------------------------------
# MLflow Configuration
# ---------------------------------------------------------------------------
tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
mlflow.set_tracking_uri(tracking_uri)

experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "customer-service-bot")
mlflow.set_experiment(experiment_name)

# Judge model — uses Gemini since it's already configured in the project
JUDGE_MODEL = "gemini:/gemini-2.5-flash"


def register_scorers():
    """Register all 5 evaluation scorers."""

    scorers = []

    # -----------------------------------------------------------------------
    # Scorer 1: Routing Accuracy (LLM-as-judge)
    #
    # Evaluates whether the coordinator routed the user's message to the
    # correct downstream agent (booking, faq, or escalation).
    # -----------------------------------------------------------------------
    routing_accuracy = make_judge(
        name="RoutingAccuracy",
        model=JUDGE_MODEL,
        description="Evaluates whether the user message was routed to the correct agent based on intent.",
        instructions="""You are evaluating the routing accuracy of an AI customer service coordinator.

Given the trace {{ trace }}, determine if the user's message was routed to the correct agent.

Routing rules:
- "booking" — user wants to book, cancel, reschedule an appointment, check availability, or anything scheduling-related
- "faq" — user has a general question about the clinic (hours, prices, policies, doctors, specialties)
- "escalation" — user is frustrated, making a complaint, or the request cannot be handled by the system

If the user is mid-conversation answering a previous question (e.g., providing a date or specialty), the route should continue to the active agent.

Return "yes" if the routing was correct, "no" if the message was sent to the wrong agent.""",
        feedback_value_type=Literal["yes", "no"],
    )
    scorers.append(("RoutingAccuracy", routing_accuracy))

    # -----------------------------------------------------------------------
    # Scorer 2: Domain Containment
    #
    # Evaluates whether the agent stayed within its assigned domain and
    # did not answer questions belonging to a different agent.
    # -----------------------------------------------------------------------
    domain_containment = make_judge(
        name="DomainContainment",
        model=JUDGE_MODEL,
        description="Evaluates whether the agent stayed within its assigned domain boundaries.",
        instructions="""You are evaluating whether an AI customer service agent stayed within its assigned domain.

Given the trace {{ trace }}, check the agent's response against these domain boundaries:

- Coordinator: Must ONLY output a JSON routing decision. Must NOT answer questions or perform actions.
- Reception: Must ONLY identify contacts and select patients. Must NOT book appointments or answer FAQ.
- Booking: Must ONLY handle scheduling (availability, reservations, cancellations). Must NOT answer FAQ or provide medical advice.
- FAQ: Must ONLY answer knowledge-base questions. Must NOT book appointments or register patients.

The agent violates domain containment if it:
- Answers a question that belongs to another agent
- Performs an action outside its responsibilities
- Provides medical advice (prohibited for ALL agents)
- Fabricates information not from tools or knowledge base

Return "yes" if the agent stayed within its domain, "no" if it crossed boundaries.""",
        feedback_value_type=Literal["yes", "no"],
    )
    scorers.append(("DomainContainment", domain_containment))

    # -----------------------------------------------------------------------
    # Scorer 3: Response Quality
    #
    # Evaluates overall quality: clarity, completeness, actionability,
    # and professional tone.
    # -----------------------------------------------------------------------
    response_quality = make_judge(
        name="ResponseQuality",
        model=JUDGE_MODEL,
        description="Evaluates the overall quality of the agent's response.",
        instructions="""You are evaluating the quality of a customer service AI agent's response.

Given the output {{ outputs }} from the agent, evaluate it on these criteria:

1. CLARITY: Is the response easy to understand? No jargon or confusing language.
2. COMPLETENESS: Does it address the user's request fully? No missing information.
3. ACTIONABILITY: Does it give the user a clear next step or answer?
4. TONE: Is it professional, friendly, and concise? Not overly verbose or robotic.
5. ACCURACY: Does it avoid vague filler phrases like "wait a minute" or "I will connect you"?

Return "yes" if the response meets all criteria at an acceptable level, "no" if it fails on any criterion significantly.""",
        feedback_value_type=Literal["yes", "no"],
    )
    scorers.append(("ResponseQuality", response_quality))

    # -----------------------------------------------------------------------
    # Scorer 4: Tool Selection
    #
    # Evaluates whether the agent used the correct tools for the user's
    # request, and didn't use tools unnecessarily.
    # -----------------------------------------------------------------------
    tool_selection = make_judge(
        name="ToolSelection",
        model=JUDGE_MODEL,
        description="Evaluates whether the agent selected and used the correct tools.",
        instructions="""You are evaluating tool usage by an AI customer service agent.

Given the trace {{ trace }}, determine if the agent used appropriate tools.

Tool usage rules:
- Reception MUST use find_contact_tool when identifying a user
- Reception MUST use create_contact_tool when registering new users
- Reception MUST use select_patient_tool to lock in a patient
- Booking MUST use check_availability_tool before presenting slots
- Booking MUST use reserve_slot_tool to hold a slot (after user confirmation)
- Booking should use cancel_appointment_tool for cancellations
- Booking should use reschedule_appointment_tool for rescheduling
- FAQ MUST use search_faq_tool before answering knowledge questions
- Coordinator should NOT use any tools (it only routes)
- No agent should call tools unnecessarily (e.g., checking availability for a greeting)

For system events like "[System Event: Payment Confirmed]", no tools should be called.

Return "yes" if tool usage was appropriate, "no" if tools were missing, incorrect, or unnecessary.""",
        feedback_value_type=Literal["yes", "no"],
    )
    scorers.append(("ToolSelection", tool_selection))

    # -----------------------------------------------------------------------
    # Scorer 5: Hallucination Check
    #
    # Evaluates whether the response contains fabricated information
    # not grounded in tool results or the knowledge base.
    # -----------------------------------------------------------------------
    hallucination_check = make_judge(
        name="HallucinationCheck",
        model=JUDGE_MODEL,
        description="Checks if the agent's response contains fabricated or ungrounded information.",
        instructions="""You are evaluating whether an AI customer service agent hallucinated information.

Given the trace {{ trace }}, check if the agent's response contains any fabricated information.

A response is considered hallucinated if it:
- Mentions specific doctor names, specialties, or availability not returned by tools
- States clinic policies, hours, or prices not found in the knowledge base search results
- Invents appointment details (dates, times, prices) not from tool results
- Claims a contact or patient exists without verifying via tools
- Fabricates tool results or simulates successful tool execution

A response is NOT hallucinated if it:
- Uses information directly from tool results
- Quotes or paraphrases knowledge base content faithfully
- Makes reasonable conversational statements (greetings, confirmations)
- Admits it doesn't have certain information

Return "yes" if the response is grounded (no hallucinations), "no" if it contains fabricated information.""",
        feedback_value_type=Literal["yes", "no"],
    )
    scorers.append(("HallucinationCheck", hallucination_check))

    # -----------------------------------------------------------------------
    # Register all scorers
    # -----------------------------------------------------------------------
    print(f"Registering {len(scorers)} scorers...")
    registered = []

    for name, scorer in scorers:
        try:
            scorer.register()
            registered.append(name)
            print(f"  ✓ {name} registered successfully")
        except Exception as e:
            print(f"  ✗ {name} registration failed: {e}", file=sys.stderr)

    print(f"\n{len(registered)}/{len(scorers)} scorers registered successfully.")

    if len(registered) < len(scorers):
        print("WARNING: Some scorers failed to register. Check errors above.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    register_scorers()
