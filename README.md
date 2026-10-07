# Customer Service Scheduling Bot (IN PROGRESS)

A multi-agent conversational customer service platform using a medical clinic as the demonstration domain.

## Overview

This project is a portfolio piece demonstrating AI engineering practices. It provides a complete simulation of a customer service workflow with a chat interface, acting as a clinic reception and scheduling assistant. 

It demonstrates:
- Multi-agent orchestration
- Agent routing
- Tool calling
- Semantic RAG (Retrieval-Augmented Generation)
- Prompt Evaluation (LLM-as-a-Judge via MLflow)
- Clean software architecture
- UI decoupling via ViewModels

The application is completely self-contained. All external service integrations (CRM, Payments, Availability) are mock implementations in the business logic layer.

## Architecture

The system uses **LangGraph** to coordinate between several specialized agents under a Supervisor pattern:
- **Coordinator Node:** Classifies user intent and routes the conversation.
- **Reception Agent:** Runs before booking to identify or register the contact (bypassed once identity is established).
- **Booking Agent:** Uses tools to manage appointments and doctor availability.
- **FAQ Agent:** Uses RAG to answer questions based on clinic documentation.
- **Escalation Node:** Interactively handles human handoff — apologises, collects contact info, and structures a single-phrase reason before routing to staff.

The architecture is strictly layered:
`UI (Streamlit) -> Application (ViewModels) -> Agents (LangGraph) -> Tools (Wrappers) -> Services (Business Logic) -> Storage (SQLite/ChromaDB)`

## Tech Stack
- **Backend Framework:** LangGraph (Python)
- **LLM Provider (Chatbot):** Google Gemini (`gemini-2.5-flash`) — used by all agents
- **LLM Provider (Evaluation Judge):** OpenAI (`gpt-4o-mini`) — used exclusively by MLflow LLM-as-a-Judge scorers
- **Database:** SQLite (managed via SQLModel)
- **Vector Store:** ChromaDB with `sentence-transformers`
- **Frontend:** Streamlit
- **Evaluation:** MLflow (LLM-as-a-Judge via OpenAI)

## Getting Started

### 1. Installation

Ensure you have Python 3.14+ and `uv` installed.

```bash
uv sync
```

### 2. Database Initialization

Initialize the SQLite database (`database.db`) with seed data:

```bash
PYTHONPATH=. uv run python scripts/init_db.py
```

### 3. Environment Configuration

Copy the example environment file and configure your LLM provider:

```bash
cp .env.example .env
```
Open `.env` and set your `GEMINI_API_KEY` (or configure OpenAI/Anthropic).

### 4. Run the Application

Launch the Streamlit interface:

```bash
PYTHONPATH=. uv run python scripts/run_ui.py
```
This will open the chat interface, complete with demo controls for external events (like payments) and a live Database Inspector.

### 5. Prompt Evaluation

The evaluation pipeline uses **MLflow** with LLM-as-a-Judge scorers backed by OpenAI `gpt-4o-mini`. The chatbot runs on Gemini; these are two independent providers — no proxying between them.

> **⚠️ IMPORTANT:** You must have both `GEMINI_API_KEY` and `OPENAI_API_KEY` set in your `.env` to run evaluations.

See [`docs/Milestone 11 - Prompt Evaluation.md`](docs/Milestone%2011%20-%20Prompt%20Evaluation.md) for full implementation details.

---

## Helper Commands

All commands assume you are **inside WSL** with the virtual environment activated:

```bash
# Enter WSL and activate the virtual environment (always do this first)
wsl
source .venv/bin/activate
```

### First-Time Setup

Run these once to initialise the database, seed the FAQ knowledge base, and wire up MLflow:

```bash
# 1. Initialise SQLite database with seed data
PYTHONPATH=. uv run python scripts/init_db.py

# 2. Ingest FAQ documents into ChromaDB (RAG knowledge base)
PYTHONPATH=. uv run python scripts/ingest.py
```

### MLflow LLMOps Workflow

Run these in order whenever prompts change or on a new environment:

```bash
# 3. Create / re-seed evaluation datasets in MLflow
#    Use --purge to fully replace existing records (e.g. after a schema change)
uv run python scripts/create_datasets.py
uv run python scripts/create_datasets.py --purge   # destructive re-seed

# 4. Register built-in scorers to the MLflow experiment
cd scripts && uv run python setup_scorers.py && cd ..

# 5. Register all agent prompts to the MLflow Prompt Registry
#    Run this after every prompt change to version it
uv run python scripts/register_prompts.py

# 6. Register the LangGraph pipeline to the MLflow Model Registry
#    Must run AFTER register_prompts.py (links model to prompt versions)
uv run python scripts/register_model.py
```

### Updating Versions (aliases)

After registering new versions, update the `@champion` alias to keep the application pointing to the right artifacts. Replace `<VERSION>` with the version number printed by the registration scripts:

```bash
# Promote a new model version to champion
uv run python scripts/manage_aliases.py model customer-service-scheduling-bot <VERSION> champion

# Promote a specific prompt version to champion
uv run python scripts/manage_aliases.py prompt coordinator-prompt  <VERSION> champion
uv run python scripts/manage_aliases.py prompt reception-prompt    <VERSION> champion
uv run python scripts/manage_aliases.py prompt booking-prompt      <VERSION> champion
uv run python scripts/manage_aliases.py prompt faq-prompt          <VERSION> champion
uv run python scripts/manage_aliases.py prompt escalation-prompt   <VERSION> champion
```

### Run Evaluation

> ⚠️ **User-exclusive prerogative** — never delegated to the AI agent (see `AGENTS.md §11`).

```bash
# Sanity check — 5 records, Correctness + intention_routing scorers (fast run)
uv run python scripts/run_evaluation.py --dataset sanity

# Full evaluation — 52 records, all 4 built-in scorers + intention_routing
uv run python scripts/run_evaluation.py --dataset full
```

At the end of every run, `scripts/eval_report.py` generates an **auto-triage report** (no LLM calls): scorer pass rates, root causes in pipeline order (`ROUTING → TOOL_USE → CONTENT → RELEVANCE → TOOL_EFFICIENCY`), a routing confusion table, judge-suspect cases and a short "inspect first" list. It also tags each trace (`triage.priority`, `triage.root_cause`, `triage.judge_suspect`) and logs `triage/report.md` + `triage/cases.csv` to the run. Local copy: `evaluation/reports/<run_id>.md`.

```bash
# Regenerate for any past run (read-only analysis; --no-write skips tagging / logging)
uv run python scripts/eval_report.py --latest
uv run python scripts/eval_report.py --run-id <run_id> --baseline <older_run_id>
```

In the MLflow UI Traces tab, filter e.g. ``tag.`triage.priority` = 'HIGH'`` instead of scrolling every trace.

Results are logged to the MLflow experiment. Open the MLflow UI to inspect traces and scores:

```bash
mlflow ui --backend-store-uri sqlite:///evaluation/mlflow.db
```

### Run the Application

```bash
PYTHONPATH=. uv run python scripts/run_ui.py
```

