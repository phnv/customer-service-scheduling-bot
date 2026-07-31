"""
Run MLflow evaluation against pre-seeded datasets.

Two modes:
  --dataset sanity  → loads 'sanity-check-5q'  (5 records, Correctness only)
  --dataset full    → loads 'prompt-eval-v1'    (50 records, all 4 scorers)

The predict_fn wraps run_agent(), mapping the dataset inputs schema
(user_message + conversation_history) to the agent's entry point.

Usage:
    uv run python scripts/run_evaluation.py --dataset sanity
    uv run python scripts/run_evaluation.py --dataset full
"""

import argparse
import os
import sys
import uuid
from typing import Any

from dotenv import load_dotenv

load_dotenv()

import mlflow
from mlflow.genai.scorers import (
    Correctness,
    RelevanceToQuery,
    ToolCallCorrectness,
    ToolCallEfficiency,
)

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
# Dataset configurations
# ---------------------------------------------------------------------------
DATASET_CONFIGS: dict[str, dict[str, Any]] = {
    "sanity": {
        "name": "sanity-check-5q",
        "scorers": [Correctness()],
        "description": "5-record sanity check — Correctness scorer only",
    },
    "full": {
        "name": "prompt-eval-v1",
        "scorers": [
            Correctness(),
            RelevanceToQuery(),
            ToolCallCorrectness(),
            ToolCallEfficiency(),
        ],
        "description": "50-record full evaluation — all 4 scorers",
    },
}


# ---------------------------------------------------------------------------
# Predict function
# ---------------------------------------------------------------------------
# Lazy import: graph.py activates mlflow.langchain.autolog() at module load,
# which must happen AFTER mlflow.set_experiment() above.
def _get_predict_fn():
    """Return the predict_fn that wraps run_agent().

    The function signature must exactly match the keys in dataset `inputs`:
        user_message:        str
        conversation_history: list[dict]

    MLflow passes inputs as **kwargs, so the parameter names here must
    match the dataset record keys precisely.
    """
    # Import deferred so autolog fires after experiment is set.
    # Add project root to sys.path so 'app' can be found when run from scripts/
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.agents.graph import run_agent

    def predict_fn(user_message: str, conversation_history: list | None = None) -> str:
        """Wrap run_agent() for mlflow.genai.evaluate().

        Each evaluation record gets a unique ephemeral conversation_id so
        that prior state from other records does not bleed across runs.
        """
        conversation_id = f"eval-{uuid.uuid4()}"
        # Prepend conversation_history as context if provided.
        # run_agent() accepts the user's message for the current turn;
        # history is currently carried in state via MemorySaver, so each
        # eval record starts fresh with its own conversation_id.
        response, _ = run_agent(
            user_message=user_message,
            conversation_id=conversation_id,
        )
        return response

    return predict_fn


# ---------------------------------------------------------------------------
# Main evaluation runner
# ---------------------------------------------------------------------------
def run_evaluation(dataset_key: str) -> None:
    if dataset_key not in DATASET_CONFIGS:
        print(f"ERROR: Unknown dataset '{dataset_key}'. Choose from: {list(DATASET_CONFIGS)}")
        sys.exit(1)

    config = DATASET_CONFIGS[dataset_key]
    dataset_name = config["name"]
    scorers = config["scorers"]
    description = config["description"]

    print("=" * 60)
    print("MLflow Agent Evaluation")
    print(f"  dataset         : {dataset_name}")
    print(f"  description     : {description}")
    print(f"  scorers         : {[s.__class__.__name__ for s in scorers]}")
    print(f"  experiment      : {experiment_name}")
    print("=" * 60)

    # Load the dataset from MLflow
    from mlflow.genai.datasets import get_dataset
    print(f"Loading dataset '{dataset_name}'...")
    try:
        dataset = get_dataset(name=dataset_name)
    except Exception as e:
        print(f"ERROR: Could not load dataset '{dataset_name}': {e}")
        print("Hint: run 'uv run python scripts/create_datasets.py' first.")
        sys.exit(1)

    df = dataset.to_df()
    print(f"Loaded {len(df)} record(s).")

    predict_fn = _get_predict_fn()

    print("Running evaluation...")
    results = mlflow.genai.evaluate(
        data=df,
        predict_fn=predict_fn,
        scorers=scorers,
    )

    print("=" * 60)
    print("Evaluation complete.")
    print(f"Results logged to MLflow experiment: '{experiment_name}'")
    print("Open the MLflow UI to inspect traces and scorer results:")
    print(f"  mlflow ui --backend-store-uri {tracking_uri}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run MLflow agent evaluation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python scripts/run_evaluation.py --dataset sanity\n"
            "  uv run python scripts/run_evaluation.py --dataset full\n"
        ),
    )
    parser.add_argument(
        "--dataset",
        choices=list(DATASET_CONFIGS.keys()),
        required=True,
        help="Which dataset to evaluate against.",
    )
    args = parser.parse_args()
    run_evaluation(args.dataset)
