import nbformat as nbf
import os

def create_notebook():
    nb = nbf.v4.new_notebook()
    
    # Markdown cell
    nb.cells.append(nbf.v4.new_markdown_cell("""\
# Prompt Evaluation Analysis

This notebook loads the results from the latest MLflow evaluation run and calculates metrics such as overall accuracy and failure rates per scorer.
"""))

    # Imports and setup
    nb.cells.append(nbf.v4.new_code_cell("""\
import os
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient

# Initialize MLflow client
db_path = os.path.abspath(os.path.join(os.getcwd(), "..", "mlflow.db")) if os.path.basename(os.getcwd()) == "notebooks" else os.path.abspath("mlflow.db")
tracking_uri = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{db_path}")
mlflow.set_tracking_uri(tracking_uri)
client = MlflowClient()

experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "customer-service-bot")
experiment = client.get_experiment_by_name(experiment_name)
print(f"Experiment ID: {experiment.experiment_id}")
"""))

    # Fetch latest run
    nb.cells.append(nbf.v4.new_code_cell("""\
# Fetch the latest full evaluation run
runs = client.search_runs(
    experiment_ids=[experiment.experiment_id],
    filter_string="tags.mlflow.runName LIKE 'prompt-eval-full%'",
    order_by=["start_time DESC"],
    max_results=1
)

if not runs:
    print("No full evaluation runs found.")
else:
    latest_run = runs[0]
    print(f"Latest Run ID: {latest_run.info.run_id}")
    print(f"Run Name: {latest_run.data.tags.get('mlflow.runName')}")
"""))

    # Load evaluation results
    nb.cells.append(nbf.v4.new_code_cell("""\
import os

# Load the local evaluation_results.csv
csv_path = os.path.abspath(os.path.join(os.getcwd(), "..", "evaluation_results.csv")) if os.path.basename(os.getcwd()) == "notebooks" else os.path.abspath("evaluation_results.csv")

if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} records from {csv_path}.")
else:
    print(f"No local evaluation_results.csv found at {csv_path}.")
"""))

    # Calculate metrics
    nb.cells.append(nbf.v4.new_code_cell("""\
# Calculate failure rates per scorer
# The columns we care about are the value columns for each scorer
scorer_cols = [col for col in df.columns if col.endswith("/value")]

print("--- Scorer Success Rates ---")
for col in scorer_cols:
    scorer_name = col.split("/")[0]
    # Handle cases where scorer might have failed to run (nulls)
    valid_responses = df[col].dropna()
    if len(valid_responses) == 0:
        print(f"{scorer_name}: No valid responses")
        continue
        
    success_count = (valid_responses.str.lower() == "yes").sum()
    total_count = len(valid_responses)
    success_rate = success_count / total_count
    
    print(f"{scorer_name:20s}: {success_rate:.1%} ({success_count}/{total_count})")
"""))

    # Save the notebook
    os.makedirs("notebooks", exist_ok=True)
    with open("notebooks/prompt_evaluation.ipynb", "w") as f:
        nbf.write(nb, f)
    
    print("Created notebooks/prompt_evaluation.ipynb")

if __name__ == "__main__":
    create_notebook()
