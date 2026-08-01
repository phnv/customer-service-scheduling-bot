"""
Shared MLflow scorers configuration for evaluation.
"""

from mlflow.genai.scorers import (
    Correctness,
    RelevanceToQuery,
    ToolCallCorrectness,
    ToolCallEfficiency,
)

INFERENCE_PARAMS = {"temperature": 0}

def get_sanity_scorers():
    """Returns scorers for the sanity check dataset."""
    return [Correctness(inference_params=INFERENCE_PARAMS)]


def get_full_scorers():
    """Returns the complete suite of scorers."""
    return [
        Correctness(inference_params=INFERENCE_PARAMS),
        RelevanceToQuery(inference_params=INFERENCE_PARAMS),
        ToolCallCorrectness(inference_params=INFERENCE_PARAMS),
        ToolCallEfficiency(inference_params=INFERENCE_PARAMS),
    ]

# test instantiation
get_full_scorers()
print("Success!")
