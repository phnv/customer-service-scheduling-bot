"""
Shared MLflow scorers configuration for evaluation.
"""

# pyrefly: ignore [missing-import]
from mlflow.genai import scorer
from mlflow.entities import Trace
from mlflow.genai.scorers import (
    Correctness,
    RelevanceToQuery,
    ToolCallCorrectness,
    ToolCallEfficiency,
)

INFERENCE_PARAMS = {"temperature": 0}

@scorer
def intention_routing(trace: Trace, expectations: dict) -> bool | None:
    """Deterministic custom scorer to verify intention routing."""
    expected_intention = expectations.get("expected_intention")
    if not expected_intention:
        return None
        
    coordinator_spans = trace.search_spans(name="coordinator")
    if not coordinator_spans:
        return False
        
    outputs = coordinator_spans[0].outputs
    if isinstance(outputs, dict):
        actual_intent = outputs.get("intent")
    else:
        actual_intent = getattr(outputs, "intent", None) or str(outputs)
        
    return actual_intent in expected_intention

def get_sanity_scorers():
    """Returns scorers for the sanity check dataset."""
    return [
        Correctness(inference_params=INFERENCE_PARAMS),
        intention_routing,
    ]


def get_full_scorers():
    """Returns the complete suite of scorers."""
    return [
        Correctness(inference_params=INFERENCE_PARAMS),
        RelevanceToQuery(inference_params=INFERENCE_PARAMS),
        ToolCallCorrectness(inference_params=INFERENCE_PARAMS),
        ToolCallEfficiency(inference_params=INFERENCE_PARAMS),
        intention_routing,
    ]

# # test instantiation
# get_full_scorers()
# print("Success!")
