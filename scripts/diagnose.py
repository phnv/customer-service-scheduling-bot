import mlflow
import pandas as pd
import json
import os
import traceback

os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///evaluation/mlflow.db"
os.environ["MLFLOW_EXPERIMENT_ID"] = "1"

# We just want to see why the judge is failing on Reception
from mlflow.genai.scorers import list_scorers
registered_scorers = list_scorers(experiment_id="1")
print("Registered:", [s.name for s in registered_scorers])

def mock_predict(**kwargs):
    # Mock what reception outputs
    return """=== INTENT ===
None

=== TOOLS ===
[]

=== CONTEXT ===
{}

=== RESPONSE ===
Hello! Are you already registered with us? If so, could you share your full name and phone number (or email) so I can pull up your file?"""

df = pd.DataFrame({
    "inputs": [{"message": "Hi, I'd like to book an appointment."}],
    "expectations": [{"criteria": "Proactively asks for contact information (name and phone/email)."}]
})

try:
    with mlflow.start_run():
        res = mlflow.genai.evaluate(
            data=df,
            predict_fn=mock_predict,
            scorers=registered_scorers,
        )
        print("Success! Tables:", list(res.tables.keys()))
except Exception as e:
    print("FAILED with Exception:", type(e).__name__, str(e))
    traceback.print_exc()
