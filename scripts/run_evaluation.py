"""
Run MLflow evaluation against pre-seeded datasets.

Two modes:
  --dataset sanity  → loads the sanity dataset (5 records, Correctness only)
  --dataset full    → loads the full dataset   (50 records, all 4 scorers)

Dataset names are read from scripts/dataset_config.json, which is written by
create_datasets.py on every successful run. Bump the name constants there and
re-run create_datasets.py — this script picks up the change automatically.

The predict_fn wraps run_agent(), mapping the dataset inputs schema
(user_message + conversation_history) to the agent's entry point.

Usage:
    uv run python scripts/run_evaluation.py --dataset sanity
    uv run python scripts/run_evaluation.py --dataset full
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

import mlflow
from scorers import get_sanity_scorers, get_full_scorers

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
# Dataset name config — loaded from scripts/dataset_config.json
# (written by create_datasets.py on every successful run)
# ---------------------------------------------------------------------------
def _load_dataset_config() -> dict:
    """Load dataset_config.json from the scripts/ directory.

    Raises SystemExit with a clear message if the file is missing so the
    operator knows to run create_datasets.py first.
    """
    config_path = Path(__file__).parent / "dataset_config.json"
    if not config_path.exists():
        print(
            f"ERROR: {config_path} not found.\n"
            "Run 'uv run python scripts/create_datasets.py' to create it."
        )
        sys.exit(1)
    with config_path.open(encoding="utf-8") as f:
        return json.load(f)


_dataset_cfg = _load_dataset_config()

# ---------------------------------------------------------------------------
# Dataset configurations
# ---------------------------------------------------------------------------
DATASET_CONFIGS: dict[str, dict[str, Any]] = {
    "sanity": {
        "name": _dataset_cfg["datasets"]["sanity"]["name"],
        "scorers": get_sanity_scorers(),
        "description": _dataset_cfg["datasets"]["sanity"]["description"],
    },
    "full": {
        "name": _dataset_cfg["datasets"]["full"]["name"],
        "scorers": get_full_scorers(),
        "description": _dataset_cfg["datasets"]["full"]["description"],
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

        MLflow passes dataset inputs as **kwargs — parameter names here must match
        the dataset record input keys exactly (user_message, conversation_history).
        See: https://mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/eval-examples.md

        Each evaluation record gets a unique ephemeral conversation_id so that
        MemorySaver state from other records does not bleed across runs.
        conversation_history is injected into initial_state directly by run_agent()
        so the agent sees full prior context on the single graph.invoke() call.
        """
        conversation_id = f"eval-{uuid.uuid4()}"
        response, _ = run_agent(
            user_message=user_message,
            conversation_id=conversation_id,
            conversation_history=conversation_history,
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
    with mlflow.start_run() as run:
        # Dynamically get the model ID based on the active provider
        provider = os.getenv("LLM_PROVIDER", "gemini").upper()
        model_id = os.getenv(f"{provider}_MODEL", "unknown")
        mlflow.set_tag("llm_model_id", model_id)
        
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

    # Auto-triage: root-cause report + trace tags (triage.*). See scripts/eval_report.py.
    from eval_report import generate_report
    generate_report(results.run_id)


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
