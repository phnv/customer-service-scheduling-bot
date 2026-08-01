"""
Register MLflow built-in scorers to the experiment for automatic evaluation.

Scorers registered here are attached at the experiment level, enabling
automatic trace evaluation in production monitoring workflows.

Note: run_evaluation.py also wires these scorers inline for offline batch runs.

Usage:
    uv run python scripts/setup_scorers.py
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

import mlflow
from scorers import get_full_scorers

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db")
experiment_id = os.getenv("MLFLOW_EXPERIMENT_ID")
experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "customer-service-scheduling-bot")

if not experiment_id:
    print("ERROR: MLFLOW_EXPERIMENT_ID is not set.")
    sys.exit(1)

mlflow.set_tracking_uri(tracking_uri)
mlflow.set_experiment(experiment_name)

# ---------------------------------------------------------------------------
# Scorer definitions
# These 4 built-in scorers cover the full evaluation surface for this agent:
#   - Correctness:         Did the agent respond correctly? (requires expected_facts)
#   - RelevanceToQuery:    Is the response relevant to the user's request?
#   - ToolCallCorrectness: Did the agent call the right tools with the right args?
#   - ToolCallEfficiency:  Did the agent avoid redundant/duplicate tool calls?
# ---------------------------------------------------------------------------
SCORERS = get_full_scorers()


def main() -> None:
    print("=" * 60)
    print("Registering MLflow Built-in Scorers")
    print(f"  experiment_id   : {experiment_id}")
    print(f"  experiment_name : {experiment_name}")
    print(f"  tracking_uri    : {tracking_uri}")
    print("=" * 60)

    for scorer in SCORERS:
        registered = scorer.register(experiment_id=experiment_id)
        print(f"  ✓ Registered: {registered.name}")

    print("=" * 60)
    print(f"Done. {len(SCORERS)} scorer(s) registered to experiment '{experiment_name}'.")
    print("=" * 60)


if __name__ == "__main__":
    main()
