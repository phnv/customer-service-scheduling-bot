#!/usr/bin/env python3
"""
Run agent evaluation using mlflow.genai.evaluate().

Usage:
    python scripts/run_evaluation.py                         # dry run: sanity-check-5q
    python scripts/run_evaluation.py --dataset prompt-eval-v1  # full eval: 50 records

The predict_fn wraps run_agent to:
  - Accept only the `user_message` field from the dataset inputs
  - Unpack the (response, state) tuple and return only the response string
"""

import argparse
import os
import sys

# Load dotenv to get all config values from .env
from dotenv import load_dotenv
load_dotenv()

# Prevent MLflow from trying to fetch model catalog updates from GitHub, which causes connection timeouts
os.environ.setdefault("MLFLOW_MODEL_CATALOG_URI", "")

# Add project root to sys.path so we can import from `app`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ---------------------------------------------------------------------------
# MLflow / environment setup
# ---------------------------------------------------------------------------
import mlflow
from mlflow.genai.datasets import get_dataset
from mlflow.genai.scorers import list_scorers

os.environ.setdefault("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db")
os.environ.setdefault("MLFLOW_EXPERIMENT_ID", "1")

# Skip the extra N+1 agent calls MLflow makes before evaluation starts.
# Our predict_fn already produces traces via @mlflow.trace, so this validation
# call is redundant and doubles the cost of a 50-record evaluation.
os.environ.setdefault("MLFLOW_GENAI_EVAL_SKIP_TRACE_VALIDATION", "true")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Run MLflow agent evaluation.")
parser.add_argument(
    "--dataset",
    default="sanity-check-5q",
    help="Name of the MLflow evaluation dataset to use (default: sanity-check-5q).",
)
args = parser.parse_args()

DATASET_NAME = args.dataset
EXPERIMENT_ID = os.environ.get("MLFLOW_EXPERIMENT_ID", "1")

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
print("=" * 60)
print("MLflow Agent Evaluation")
print("=" * 60)
print()

# ---------------------------------------------------------------------------
# Load dataset
# ---------------------------------------------------------------------------
print("Loading evaluation dataset...")
try:
    dataset = get_dataset(DATASET_NAME)
    df = dataset.to_df()
    print(f"  Dataset : {DATASET_NAME}")
    print(f"  Records : {len(df)}")
    if len(df) > 0:
        sample_inputs = df.iloc[0]["inputs"]
        print(f"  Input keys: {list(sample_inputs.keys())}")
    print()
except Exception as e:
    print(f"✗ Failed to load dataset '{DATASET_NAME}': {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Load registered scorers
# ---------------------------------------------------------------------------
print("Loading registered scorers...")
try:
    registered_scorers = list_scorers(experiment_id=EXPERIMENT_ID)

    if not registered_scorers:
        print("  ⚠ No registered scorers found in experiment.")
        print("  Register scorers first: python scripts/register_scorers.py")
        sys.exit(1)

    print(f"  Found {len(registered_scorers)} scorer(s):")
    for scorer in registered_scorers:
        print(f"    - {scorer.name}")
    print()
except Exception as e:
    print(f"✗ Failed to load scorers: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Import agent entry point
# ---------------------------------------------------------------------------
print("Importing agent entry point...")
try:
    from app.agents.graph import run_agent
    print("  ✓ Imported run_agent from app.agents.graph")
    print()
except ImportError as e:
    print(f"✗ Failed to import agent: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# predict_fn wrapper
#
# Why this wrapper exists:
#   mlflow.genai.evaluate() calls predict_fn(**inputs) — it unpacks the dataset
#   inputs dict as keyword arguments. Our dataset records have three fields:
#     { user_message, conversation_history, agent_under_test }
#   but run_agent only accepts (user_message, conversation_id).
#   The wrapper absorbs the extra kwargs and returns only the response string
#   (run_agent returns a (response, state) tuple which MLflow cannot score).
# ---------------------------------------------------------------------------
def predict_fn(
    user_message: str,
    conversation_history: list | None = None,
    agent_under_test: str | None = None,
    **kwargs,
) -> str:
    response, _state = run_agent(user_message=user_message)
    return response

# ---------------------------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------------------------
print("=" * 60)
print("Running Evaluation")
print("=" * 60)
print()
print(f"  Dataset : {DATASET_NAME} ({len(df)} records)")
print(f"  Scorers : {[s.name for s in registered_scorers]}")
print(f"  Agent   : app.agents.graph.run_agent")
print()

try:
    results = mlflow.genai.evaluate(
        data=df,
        predict_fn=predict_fn,
        scorers=registered_scorers,
    )

    print()
    print("=" * 60)
    print("Evaluation Results")
    print("=" * 60)
    print()

    if hasattr(results, "metrics") and results.metrics:
        print("Aggregate Metrics:")
        for metric_name, value in results.metrics.items():
            if isinstance(value, float):
                print(f"  {metric_name}: {value:.3f}")
            else:
                print(f"  {metric_name}: {value}")
        print()

    if hasattr(results, "eval_results_table"):
        output_file = "evaluation_results.csv"
        results.eval_results_table.to_csv(output_file, index=False)
        print(f"  ✓ Detailed results saved to: {output_file}")

    print()
    print("=" * 60)
    print("Evaluation Complete")
    print("=" * 60)

except Exception as e:
    print(f"✗ Evaluation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
