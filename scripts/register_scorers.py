"""
Register evaluation scorers for prompt evaluation.

Registers 3 scorers into the MLflow experiment:
  1. Response Quality     — LLM-as-judge via make_judge()
  2. Expectations Met     — LLM-as-judge via make_judge()
  3. Faithfulness         — LLM-as-judge via make_judge() (Replaces HallucinationCheck)
  
Note: Trace-based scorers (RoutingAccuracy, ToolSelection, etc.) were replaced 
by deterministic metrics in run_evaluation.py to eliminate agentic judge costs.

Usage:
    uv run python evaluation/register_scorers.py
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
tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db")
mlflow.set_tracking_uri(tracking_uri)

experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "customer-service-bot")
mlflow.set_experiment(experiment_name)

# Judge model — uses OpenAI for evaluation while the system uses Gemini
JUDGE_MODEL = "openai:/gpt-4o-mini"


def register_scorers():
    """Register all 5 evaluation scorers."""

    scorers = []

    # -----------------------------------------------------------------------
    # We removed RoutingAccuracy, DomainContainment, ToolSelection, 
    # and HallucinationCheck because their `{{ trace }}` variables caused
    # catastrophic Agentic Judge infinite loops with gpt-4o-mini.
    # These checks are now handled deterministically by custom Python metrics
    # (exact_match, etc.) in run_evaluation.py, costing 0 tokens.
    # -----------------------------------------------------------------------


    # -----------------------------------------------------------------------
    # Scorer 1: Response Quality
    # -----------------------------------------------------------------------
    response_quality = make_judge(
        name="ResponseQuality",
        model=JUDGE_MODEL,
        description="Evaluates the overall quality of the agent's response.",
        instructions="""
    You are evaluating the quality of an agent's response.
    
    Extract the text under the === RESPONSE === section from the output {{ outputs }}.
    Evaluate the overall quality of this response based on:
    1. Clarity and coherence
    2. Professionalism and tone
    3. Helpfulness to the user
    
    Return "yes" if the response is of high quality, "no" otherwise.
    """,
        feedback_value_type=Literal["yes", "no"],
    )
    scorers.append(("ResponseQuality", response_quality))

    # -----------------------------------------------------------------------
    # Scorer 2: ExpectationsMet
    # -----------------------------------------------------------------------
    expectations_met = make_judge(
        name="ExpectationsMet",
        model=JUDGE_MODEL,
        description="Evaluates whether the agent met the specific expectations defined in the dataset.",
        instructions="""
    You are evaluating whether an agent met specific expectations.
    
    Given the expectation criteria: {{ expectations }}
    
    Extract the text under the === RESPONSE === section from the output {{ outputs }}.
    Determine if this response successfully fulfills the provided expectations.
    
    Return "yes" if the expectations are met, "no" if they are not.
    """,
        feedback_value_type=Literal["yes", "no"],
    )
    scorers.append(("ExpectationsMet", expectations_met))
    
    # -----------------------------------------------------------------------
    # Scorer 3: Faithfulness (Replaces HallucinationCheck)
    # -----------------------------------------------------------------------
    faithfulness = make_judge(
        name="Faithfulness",
        model=JUDGE_MODEL,
        description="Checks if the agent's response is grounded in the tool context.",
        instructions="""
    You are evaluating whether an agent's response is faithful to the provided context.
    
    From the output {{ outputs }}, extract two sections:
    1. The text under === CONTEXT ===
    2. The text under === RESPONSE ===
    
    Determine if the information in the RESPONSE is completely supported by and grounded in the CONTEXT.
    If the RESPONSE contains claims, facts, or data not present in the CONTEXT, return "no".
    If the RESPONSE is entirely supported by the CONTEXT, return "yes".
    """,
        feedback_value_type=Literal["yes", "no"],
    )
    scorers.append(("Faithfulness", faithfulness))

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
