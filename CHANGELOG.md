# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **MLflow Evaluation Pipeline completely repaired and hardened against MLflow 2.14+ breaking changes.**
  - **Dataset Schema (Expectations):** Stripped all `None` values and empty keys from the `expectations` dictionaries during dataset creation. MLflow 2.14+ natively parses this column into `Expectation` objects and will instantly crash the run (`MlflowException: The 'value' field must be specified`) if any key evaluates to `None`.
  - **Trace Mode Hijacking (`KeyError: 'outputs'`):** Added the `@mlflow.trace` decorator directly to the top-level `predict_fn`. Previously, the inner `run_agent` trace was silently hijacking the evaluation and dropping the formatted string output, resulting in the evaluation extracting the raw Python tuple instead and crashing heuristics.
  - **Result Table Extraction (`KeyError: 'eval_results_table'`):** Updated the metric extraction logic to query `results.tables["eval_results"]` instead of `eval_results_table`, reflecting MLflow's unannounced internal rename.
  - **Rebuilt Golden Datasets:** Successfully executed `--purge` to rebuild the SQLite database and flush out the corrupted `sanity-check-5q` and `prompt-eval-v1` datasets.

---

> **CRITICAL WARNING REGARDING DEPENDENCY UPDATES (Specifically MLflow)**
> 
> The fixes implemented above were required because MLflow introduced severe, undocumented breaking changes to its `mlflow.genai.evaluate` API within the `2.x.x` minor release track (specifically `2.14.x`). These changes altered expected DataFrame columns, hijacked output mappings via Trace Mode, and enforced strict Pydantic schemas on dataset dictionaries.
> 
> **DO NOT UPDATE MLFLOW TO VERSION 3.x.x.**
> Given the instability of the `2.x.x` API, any future major update to MLflow `3.x.x` is virtually guaranteed to completely break the Prompt Evaluation pipeline, the LLM Scorers, and the SQLite metric extraction. 
> 
> If an upgrade to `3.x.x` is ever proposed:
> 1. It must be isolated in a dedicated migration sprint.
> 2. The entire evaluation suite (`sanity-check-5q`) must be dry-run to identify schema changes.
> 3. The `predict_fn` trace mapping must be explicitly re-verified to ensure `{{ outputs }}` still receives the formatted string.
