"""
Run prompt evaluation using MLflow.

Loads the evaluation dataset, wraps run_agent() as the predict function,
runs mlflow.genai.evaluate() with all registered scorers, and saves results.

Usage:
    uv run python scripts/run_evaluation.py               # Full evaluation
    uv run python scripts/run_evaluation.py --dry-run      # 3 records only
    uv run python scripts/run_evaluation.py --dataset NAME # Use a specific dataset
"""

import argparse
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path so 'app' is importable
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from dotenv import load_dotenv

load_dotenv()

import mlflow
from mlflow.genai.datasets import search_datasets

# ---------------------------------------------------------------------------
# MLflow Configuration
# ---------------------------------------------------------------------------
tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
mlflow.set_tracking_uri(tracking_uri)

experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "customer-service-bot")
mlflow.set_experiment(experiment_name)

# Auto-instrument LangChain/LangGraph
mlflow.langchain.autolog()

# ---------------------------------------------------------------------------
# Monkeypatch MLflow to handle Gemini 2.5 JSON structured output error
# ---------------------------------------------------------------------------
try:
    from mlflow.genai.judges.adapters import utils as judge_utils
    
    _orig_is_response_format_error = judge_utils.is_response_format_error
    
    def _patched_is_response_format_error(error_message: str) -> bool:
        if "response mime type" in error_message.lower():
            return True
        return _orig_is_response_format_error(error_message)
        
    judge_utils.is_response_format_error = _patched_is_response_format_error
except ImportError:
    pass

DEFAULT_DATASET = "prompt-eval-v1"


def get_predict_fn():
    """
    Returns a predict function that wraps run_agent().

    MLflow calls predict_fn(**inputs) — it unpacks the dataset's inputs dict
    as keyword arguments. Our dataset has:
        inputs.user_message: str
        inputs.conversation_history: list[dict]
        inputs.agent_under_test: str

    The wrapper handles multi-turn by replaying conversation_history through
    run_agent() with a fresh conversation_id per evaluation record.
    """
    from app.agents.graph import run_agent

    def predict_fn(user_message: str, conversation_history: list = None, agent_under_test: str = None) -> str:
        """
        Wraps run_agent() for MLflow evaluation.

        For multi-turn records, replays conversation_history first,
        then sends the final user_message.
        """
        conversation_id = str(uuid.uuid4())

        # Replay conversation history (if any) to build up agent state
        if conversation_history:
            for turn in conversation_history:
                if turn.get("role") == "user":
                    try:
                        run_agent(turn["content"], conversation_id=conversation_id)
                    except Exception:
                        # History replay failures are non-fatal — the agent may
                        # not have enough context but we still evaluate the final turn
                        pass

        # Run the actual evaluation turn
        response, _state = run_agent(user_message, conversation_id=conversation_id)
        return response

    return predict_fn


def load_dataset(dataset_name: str):
    """Load an MLflow dataset by name."""
    datasets = search_datasets(filter_string=f"name = '{dataset_name}'")
    if not datasets:
        print(f"ERROR: Dataset '{dataset_name}' not found.", file=sys.stderr)
        print("Run 'uv run python scripts/create_dataset.py' first.", file=sys.stderr)
        sys.exit(1)
    return datasets[0]


def load_registered_scorers():
    """Load all scorers registered in the experiment."""
    from mlflow.genai.scorers import list_scorers

    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        print(f"ERROR: Experiment '{experiment_name}' not found.", file=sys.stderr)
        sys.exit(1)

    try:
        scorers = list_scorers(experiment_id=experiment.experiment_id)
        if not scorers:
            print("WARNING: No registered scorers found.", file=sys.stderr)
            print("Run 'uv run python scripts/register_scorers.py' first.", file=sys.stderr)
            return []
        print(f"   Loaded {len(scorers)} scorers: {[s.name for s in scorers]}")
        return scorers
    except Exception as e:
        print(f"WARNING: Could not load registered scorers: {e}", file=sys.stderr)
        print("Evaluation will proceed without scorers.", file=sys.stderr)
        return []


def run_evaluation(dataset_name: str, dry_run: bool = False):
    """Run the full evaluation pipeline."""

    print("=" * 60)
    print("  Prompt Evaluation — Customer Service Scheduling Bot")
    print("=" * 60)

    # 1. Load dataset
    print(f"\n📦 Loading dataset: {dataset_name}")
    dataset = load_dataset(dataset_name)
    df = dataset.to_df()
    total_records = len(df)

    if dry_run:
        df = df.head(3)
        print(f"   🔬 DRY RUN: Using first 3 of {total_records} records")
    else:
        print(f"   Records: {total_records}")

    # 2. Estimate runtime
    records_to_run = len(df)
    est_min = (records_to_run * 30) / 60  # ~30s per record with Gemini
    est_max = (records_to_run * 60) / 60  # ~60s per record worst case
    print(f"   ⏱  Estimated time: {est_min:.0f}–{est_max:.0f} minutes")

    # 3. Build predict function
    print("\n🔧 Building predict function (wrapping run_agent)...")
    predict_fn = get_predict_fn()

    # 3.5. Load scorers
    print("\n📋 Loading registered scorers...")
    scorers = load_registered_scorers()
    if not scorers:
        print("ERROR: No scorers available. Cannot proceed.", file=sys.stderr)
        sys.exit(1)

    # 4. Run evaluation
    run_name = f"prompt-eval-{'dry-run' if dry_run else 'full'}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"\n🚀 Starting evaluation run: {run_name}")
    print(f"   Records: {records_to_run}")

    start_time = time.time()

    with mlflow.start_run(run_name=run_name):
        # Log metadata
        mlflow.log_params({
            "dataset": dataset_name,
            "dry_run": str(dry_run),
            "records": records_to_run,
            "predict_fn": "run_agent",
            "scorers": str([s.name for s in scorers]),
        })

        # Run evaluation with MLflow
        results = mlflow.genai.evaluate(
            data=dataset if not dry_run else df,
            predict_fn=predict_fn,
            scorers=scorers,
        )

        elapsed = time.time() - start_time

        # Log timing
        mlflow.log_metric("evaluation_time_seconds", elapsed)
        mlflow.log_metric("seconds_per_record", elapsed / max(records_to_run, 1))

    # 5. Save results
    output_file = "evaluation_results.csv"
    if results and hasattr(results, "tables"):
        for table_name, table_df in results.tables.items():
            table_df.to_csv(output_file, index=False)
            print(f"\n📄 Results saved to: {output_file}")
            break
    elif results and hasattr(results, "metrics"):
        print(f"\n📊 Metrics:")
        for metric, value in results.metrics.items():
            print(f"   {metric}: {value}")

    # 6. Summary
    print(f"\n{'=' * 60}")
    print(f"  ✅ Evaluation complete!")
    print(f"  Run name: {run_name}")
    print(f"  Time: {elapsed:.1f}s ({elapsed/max(records_to_run,1):.1f}s/record)")
    print(f"  Results: {output_file}")
    print(f"{'=' * 60}")

    if dry_run:
        print(f"\n💡 This was a dry run (3 records). Run without --dry-run for full evaluation.")

    return results


def main():
    parser = argparse.ArgumentParser(description="Run prompt evaluation with MLflow")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run evaluation on first 3 records only (sanity check)",
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help=f"Dataset name to use (default: {DEFAULT_DATASET})",
    )
    args = parser.parse_args()

    run_evaluation(dataset_name=args.dataset, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
