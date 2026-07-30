import mlflow
from mlflow.genai.scorers import delete_scorer

import os
os.environ["MLFLOW_EXPERIMENT_ID"] = "1"
mlflow.set_tracking_uri("sqlite:///evaluation/mlflow.db")

obsolete = ["ResponseQuality", "ExpectationsMet", "Faithfulness"]
for scorer in obsolete:
    try:
        delete_scorer(name=scorer, version="all")
        print(f"Deleted {scorer}")
    except Exception as e:
        print(f"Failed to delete {scorer}: {e}")
