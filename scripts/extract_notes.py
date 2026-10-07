"""
Extract notes added to MLflow traces into a CSV table.

Usage:
    uv run python scripts/extract_notes.py --latest
    uv run python scripts/extract_notes.py --run-id <run_id>
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

import mlflow
from mlflow import MlflowClient

REPORTS_DIR = Path(__file__).resolve().parent.parent / "evaluation" / "reports"

def latest_evaluation_run_id(client: MlflowClient, experiment_id: str) -> str:
    runs = client.search_runs([experiment_id], order_by=["attributes.start_time DESC"], max_results=20)
    for run in runs:
        linked = mlflow.search_traces(
            locations=[experiment_id],
            run_id=run.info.run_id,
            include_spans=False,
            max_results=1,
            return_type="list",
        )
        if linked:
            return run.info.run_id
    raise SystemExit(f"No evaluation run found in experiment '{experiment_id}'.")

def extract_notes(run_id: str, include_sessions: bool = False):
    client = MlflowClient()
    run = client.get_run(run_id)
    
    traces = mlflow.search_traces(
        locations=[run.info.experiment_id],
        run_id=run_id,
        include_spans=False,
        return_type="list",
    )
    
    if not traces:
        raise SystemExit(f"No traces found for run {run_id}.")

    rows = []
    seen_sessions = set()
    for t in traces:
        tags = t.info.tags or {}
        case_id = tags.get("index") or t.info.trace_id
        
        # The MLflow UI trace notes are saved as HUMAN assessments named 'mlflow.notes'
        # Since a trace can be scored multiple times, we sort by update time and take the latest.
        note_assessments = sorted(
            [a for a in (t.info.assessments or []) if a.name == "mlflow.notes"],
            key=lambda a: a.last_update_time_ms or 0
        )
        
        if note_assessments:
            latest_note_obj = note_assessments[-1]
            is_session = "mlflow.trace.session" in (latest_note_obj.metadata or {})
            
            if is_session:
                if not include_sessions:
                    continue
                session_id = latest_note_obj.metadata.get("mlflow.trace.session")
                if session_id in seen_sessions:
                    continue
                seen_sessions.add(session_id)
            
            # The actual text of the note is stored in the `value` field
            latest_note = latest_note_obj.value
            if latest_note:
                rows.append({
                    "case_id": case_id,
                    "trace_id": t.info.trace_id,
                    "level": "session" if is_session else "trace",
                    "note": str(latest_note).strip()
                })
            
    if not rows:
        print(f"No traces with notes found in run {run_id}.")
        return

    df = pd.DataFrame(rows)
    csv_data = df.to_csv(index=False)
    
    # Save locally to evaluation/reports/
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    local_path = REPORTS_DIR / f"{run_id}_notes.csv"
    local_path.write_text(csv_data, encoding="utf-8")
    
    # Save to MLflow run artifacts (same folder as triage/cases.csv)
    client.log_text(run_id, csv_data, "triage/notes.csv")
    
    print("=" * 60)
    print("Trace Notes Extracted")
    print(f"  Notes found: {len(rows)}")
    print(f"  Local CSV  : {local_path}")
    print(f"  MLflow UI  : Saved as artifact 'triage/notes.csv' in run {run_id}")
    print("=" * 60)

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Extract trace notes to a CSV.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--run-id", help="Evaluation run to analyse.")
    target.add_argument("--latest", action="store_true", help="Latest run with linked traces.")
    parser.add_argument("--include-sessions", action="store_true", help="Include notes added at the multi-turn session level.")
    args = parser.parse_args()

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db"))

    run_id = args.run_id
    if args.latest:
        experiment_id = os.getenv("MLFLOW_EXPERIMENT_ID")
        if not experiment_id:
            print("ERROR: MLFLOW_EXPERIMENT_ID is not set (needed for --latest).")
            sys.exit(1)
        run_id = latest_evaluation_run_id(MlflowClient(), experiment_id)

    extract_notes(run_id, include_sessions=args.include_sessions)

if __name__ == "__main__":
    main()
