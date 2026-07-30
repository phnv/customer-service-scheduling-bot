import mlflow
from mlflow.metrics import make_metric
import pandas as pd
import os

os.environ["MLFLOW_EXPERIMENT_ID"] = "1"
mlflow.set_tracking_uri("sqlite:///evaluation/mlflow.db")

df = pd.DataFrame({"inputs": [{"user_message": "hi"}], "expectations": [{"criteria": "hi"}]})

cache = {}
def cached_predict(user_message, **kwargs):
    print("CALLED FOR", user_message)
    if user_message in cache:
        return cache[user_message]
    cache[user_message] = "{}"
    return cache[user_message]

# Wrapper for mlflow because it passes **row to predict_fn
def predict_wrapper(**kwargs):
    return cached_predict(kwargs.get("user_message", ""))

route_match = make_metric(eval_fn=lambda p,t,m: pd.Series([1.0]), greater_is_better=True, name="route_match")

from mlflow.genai.scorers import list_scorers
registered = list_scorers(experiment_id="1")

with mlflow.start_run():
    # 1. GenAI evaluation
    mlflow.genai.evaluate(data=df, predict_fn=predict_wrapper, scorers=registered)
    # 2. Heuristic evaluation
    mlflow.evaluate(model=predict_wrapper, data=df, model_type="text", extra_metrics=[route_match])
