import mlflow
client = mlflow.MlflowClient()
traces = client.search_traces(experiment_ids=['1'], max_results=5)
for t in traces:
    print(f"Trace ID: {t.info.request_id}")
    trace = client.get_trace(t.info.request_id)
    print("Assessments:")
    for a in trace.data.assessments:
        print(f" - {a.name}: {a.source.error_code} - {a.source.error_message}")
        if not a.source.error_code:
            print(f"   Value: {a.value}")
