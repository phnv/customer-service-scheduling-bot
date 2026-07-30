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
import json
import pandas as pd

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
from mlflow.genai.scorers import list_scorers, RetrievalGroundedness

os.environ.setdefault("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db")
os.environ.setdefault("MLFLOW_EXPERIMENT_ID", "1")
os.environ.setdefault("MLFLOW_EVALUATION_MAX_WORKERS", "1")

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
# Why this wrapper exists: UNDO THIS WORKAROUND AT SOME POINT
#   mlflow.genai.evaluate() calls predict_fn(**inputs) — it unpacks the dataset
#   inputs dict as keyword arguments. Our dataset records have three fields:
#     { user_message, conversation_history, agent_under_test }
#   but run_agent only accepts (user_message, conversation_id).
#   The wrapper absorbs the extra kwargs and returns only the response string
#   (run_agent returns a (response, state) tuple which MLflow cannot score).
# ---------------------------------------------------------------------------
@mlflow.trace
def predict_fn(
    user_message: str,
    conversation_history: list | None = None,
    agent_under_test: str | None = None,
    **kwargs,
) -> dict:
    response, state = run_agent(user_message=user_message)
    
    intent = state.get("intent")
    
    # Extract tools and context
    tools = []
    context = ""
    for msg in state.get("messages", []):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for call in msg.tool_calls:
                tools.append(call["name"])
        elif hasattr(msg, "name") and msg.name in tools:
            # It's a tool output message
            context += f"Tool {msg.name} output: {msg.content}\n"
            
    # Remove duplicates from tools
    tools = list(set(tools))

    output_text = f"=== INTENT ===\n{state.get('intent', 'None')}\n\n"
    output_text += f"=== TOOLS ===\n{json.dumps(tools)}\n\n"
    output_text += f"=== CONTEXT ===\n{json.dumps(context)}\n\n"
    output_text += f"=== RESPONSE ===\n{response}\n"
    
    if not context.strip():
        context = "No tool called"
        
    return {
        "response": output_text,
        "context": context
    }

# ---------------------------------------------------------------------------
# Zero-Token Python Heuristics (Replaces Trace Judges)
# -----------------------------------------------------------------------

import re
import json
from mlflow.genai import scorer
from mlflow.entities import Feedback
from mlflow.genai.scorers import ToolCallCorrectness

def extract_section(text, header):
    pattern = rf"=== {header} ===\n(.*?)(?=\n===|$)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

@scorer(name="route_match")
def route_match_scorer(outputs: dict, expectations: dict) -> Feedback:
    try:
        t_intent = expectations.get("expected_route")
        if not t_intent:
            return Feedback(score=1.0, justification="No route expectation provided.")
        
        response_text = outputs.get("response", "")
        p_intent = extract_section(response_text, "INTENT")
        
        score = 1.0 if p_intent == t_intent else 0.0
        return Feedback(score=score, justification=f"Expected: {t_intent}, Got: {p_intent}")
    except Exception as e:
        return Feedback(score=0.0, justification=f"Error: {e}")

# ---------------------------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------------------------
print("=" * 60)
print("Running Evaluation (Partitioned by Agent)")
print("=" * 60)
print()

# Map of which metrics to calculate for which agent
agent_heuristics = {
    "coordinator": ["route_match"],
    "reception": ["route_match", "tool_match"],
    "booking": ["route_match", "tool_match"],
    "faq": ["route_match", "tool_match"],
}

agents_to_test = ["coordinator", "reception", "booking", "faq"]

for agent in agents_to_test:
    partition_name = f"{DATASET_NAME}-{agent}"
    
    print(f"--- Evaluating Agent: {agent.upper()} ---")
    try:
        dataset = get_dataset(partition_name)
        df = dataset.to_df()
        
        if len(df) == 0:
            print(f"  Skipping {partition_name}: 0 records.\n")
            continue
            
        heuristics_to_run = agent_heuristics.get(agent, [])
        active_scorers = list(registered_scorers)
        
        if "route_match" in heuristics_to_run:
            active_scorers.append(route_match_scorer)
        if "tool_match" in heuristics_to_run:
            active_scorers.append(ToolCallCorrectness(should_exact_match=True))
            
        groundedness = RetrievalGroundedness(model="openai:/gpt-4o-mini")
        active_scorers.append(groundedness)
            
        scorer_names = [s.name if hasattr(s, "name") else s.__class__.__name__ for s in active_scorers]
        
        print(f"  Dataset : {partition_name} ({len(df)} records)")
        print(f"  Scorers : {scorer_names}")
        
        with mlflow.start_run() as run:
            results = mlflow.genai.evaluate(
                data=df,
                predict_fn=predict_fn,
                scorers=active_scorers,
            )
        
        if hasattr(results, "metrics") and results.metrics:
            print("  Metrics:")
            for metric_name, value in results.metrics.items():
                if isinstance(value, float):
                    print(f"    {metric_name}: {value:.3f}")
                else:
                    print(f"    {metric_name}: {value}")
                    
        if "eval_results" in getattr(results, "tables", {}):
            output_file = f"evaluation_results_{agent}.csv"
            results.tables["eval_results"].to_csv(output_file, index=False)
            print(f"  ✓ Detailed results saved to: {output_file}")
            
        print()
    except Exception as e:
        print(f"  ✗ Evaluation failed for {partition_name}: {e}")
        print()

print("=" * 60)
print("All Evaluations Complete")
print("=" * 60)
