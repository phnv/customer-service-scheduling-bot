import mlflow
import json

client = mlflow.MlflowClient(tracking_uri="sqlite:///evaluation/mlflow.db")
runs = client.search_runs(experiment_ids=["1"])
last_run = runs[0]

traces = client.search_traces(experiment_ids=["1"], run_id=last_run.info.run_id, max_results=1)
if traces:
    trace = traces[0]
    print(trace.info.request_id)
    # Check assessments (which contain the scorer results)
    for assessment in trace.info.assessments:
        print(f"Scorer: {assessment.name}")
        print(f"Error: {assessment.error_message}")
