import os
import subprocess
import mlflow
from dotenv import load_dotenv

load_dotenv()

runs = {
    "omniscient-ram-469": "de8ed242585b4c1eaab53030ca7f9e86",
    "magnificent-crab-619": "5879df51990c48218c0e672f964dc73a",
    "unique-crab-584": "0209c2e6d4294abbb7a937705e1e718a",
    "upbeat-wolf-376": "35819fe559ee4a5b9d1e091f8146c94b"
}

for name, run_id in runs.items():
    print(f"Processing {name} ({run_id})...")
    try:
        # Load the evaluation results table
        df = mlflow.load_table("eval_results_table", run_ids=[run_id])
        
        # Save to a temporary CSV file
        csv_path = f"temp_eval_{name}.csv"
        df.to_csv(csv_path, index=False)
        
        # Make sure evaluation folder exists
        os.makedirs("evaluation", exist_ok=True)
        
        report_path = f"evaluation/report_{name}.md"
        
        # Run analyze_results.py
        subprocess.run(["uv", "run", "python", "scripts/analyze_results.py", csv_path, "--output", report_path], check=True)
        
        # Delete temporary CSV
        if os.path.exists(csv_path):
            os.remove(csv_path)
        
        print(f"Successfully generated {report_path}")
    except Exception as e:
        print(f"Error processing {name}: {e}")
