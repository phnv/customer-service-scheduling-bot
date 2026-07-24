import mlflow
import pandas as pd
import os

client = mlflow.MlflowClient()
run = client.search_runs(experiment_ids=['1'])[0]
df = mlflow.load_table('eval_results_table', run_ids=[run.info.run_id])
for col in df.columns:
    if 'error' in col.lower() or 'error_message' in col.lower():
        print(f'\n--- {col} ---')
        print(df[col].dropna().iloc[0] if not df[col].dropna().empty else 'No error recorded')
