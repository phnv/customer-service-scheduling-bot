"""
Register the LangGraph multi-agent pipeline to the MLflow Model Registry.

Uses the 'models-from-code' pattern: MLflow logs the path to graph.py and
reconstructs the model at load time by importing it — no pickle serialization.

The model is linked to all registered prompt URIs (from register_prompts.py)
via the `prompts` argument, establishing an explicit lineage between the
agent's prompts and its registered model version.

Prerequisites:
    Run register_prompts.py first so .latest_prompt_uris.json exists:
        uv run python scripts/register_prompts.py

Usage:
    uv run python scripts/register_model.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import mlflow

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db")
experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "customer-service-scheduling-bot")

mlflow.set_tracking_uri(tracking_uri)
mlflow.set_experiment(experiment_name)

PROJECT_ROOT = Path(__file__).parent.parent
GRAPH_PATH = PROJECT_ROOT / "app" / "agents" / "graph.py"
URIS_PATH = Path(__file__).parent / ".latest_prompt_uris.json"
REGISTERED_MODEL_NAME = "customer-service-scheduling-bot"

# Add project root to path so mlflow can import `app` when evaluating models-from-code locally
sys.path.insert(0, str(PROJECT_ROOT))


def load_prompt_uris() -> list[str]:
    """Load prompt URIs written by register_prompts.py."""
    if not URIS_PATH.exists():
        print(
            "WARNING: .latest_prompt_uris.json not found. "
            "Run register_prompts.py first to link prompts to this model version."
        )
        return []
    uris = json.loads(URIS_PATH.read_text())
    return list(uris.values())


def main() -> None:
    prompt_uris = load_prompt_uris()

    print("=" * 60)
    print("Registering LangGraph Agent to MLflow Model Registry")
    print(f"  model_name   : {REGISTERED_MODEL_NAME}")
    print(f"  graph_path   : {GRAPH_PATH}")
    print(f"  experiment   : {experiment_name}")
    print(f"  prompt_links : {len(prompt_uris)} prompt(s)")
    print("=" * 60)

    if not GRAPH_PATH.exists():
        print(f"ERROR: graph.py not found at {GRAPH_PATH}")
        sys.exit(1)

    # Signature: maps the dataset inputs schema to the agent's output.
    # user_message + conversation_history mirrors the predict_fn in run_evaluation.py.
    sample_input = {
        "user_message": "I'd like to book an appointment.",
        "conversation_history": [],
    }
    sample_output = {
        "response": "Hello! Are you already registered with us? Could you share your name and phone number?",
    }
    signature = mlflow.models.infer_signature(sample_input, sample_output)

    with mlflow.start_run() as run:
        model_info = mlflow.langchain.log_model(
            lc_model=str(GRAPH_PATH),
            artifact_path="model",
            signature=signature,
            registered_model_name=REGISTERED_MODEL_NAME,
            prompts=prompt_uris if prompt_uris else None,
            code_paths=[str(PROJECT_ROOT / "app")],
        )

        print(f"  ✓ Model registered: {REGISTERED_MODEL_NAME}")
        print(f"  ✓ Version         : {model_info.registered_model_version}")
        print(f"  ✓ Run ID          : {run.info.run_id}")

    print()
    print("Set the champion alias with:")
    print(f"  uv run python scripts/manage_aliases.py model {REGISTERED_MODEL_NAME} {model_info.registered_model_version} champion")
    print("=" * 60)


if __name__ == "__main__":
    main()
