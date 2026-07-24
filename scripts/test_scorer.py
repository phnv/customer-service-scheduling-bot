import os
# Load dotenv to get all config values from .env
from dotenv import load_dotenv
load_dotenv()

# Prevent MLflow from trying to fetch model catalog updates from GitHub, which causes connection timeouts
os.environ.setdefault("MLFLOW_MODEL_CATALOG_URI", "")

import mlflow
from mlflow.genai.judges import make_judge
from typing import Literal

mlflow.set_tracking_uri("sqlite:///evaluation/mlflow.db")
mlflow.set_experiment("customer-service-bot")

import mlflow.genai.judges.adapters.utils
original_is_response_format_error = mlflow.genai.judges.adapters.utils.is_response_format_error
def new_is_response_format_error(error_message: str) -> bool:
    return original_is_response_format_error(error_message) or "response mime type: 'application/json' is unsupported" in error_message.lower()
mlflow.genai.judges.adapters.utils.is_response_format_error = new_is_response_format_error

# Create the simplest trace scorer
judge = make_judge(
    name="TestTraceJudge",
    model="openai:/gpt-4o-mini",
    description="Test",
    instructions="Given {{ trace }}, return 'yes'.",
    feedback_value_type=Literal["yes", "no"]
)

client = mlflow.MlflowClient()
traces = client.search_traces(experiment_ids=['1'], max_results=1)

if traces:
    trace = client.get_trace(traces[0].info.request_id)
    print("Testing judge on trace...")
    try:
        # evaluate trace
        res = judge(trace=trace)
        print("Result:", res)
    except Exception as e:
        print("Error evaluating judge:")
        import traceback
        traceback.print_exc()
else:
    print("No traces found.")
