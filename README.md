# Customer Service Scheduling Bot

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
- **Escalation Node:** Handles unsupported requests and human handoff.

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

The evaluation pipeline uses **MLflow** with 6 LLM-as-a-Judge scorers backed by OpenAI `gpt-4o-mini`. The chatbot runs on Gemini; these are two independent providers — no proxying between them.

> **⚠️ IMPORTANT:** You must have both `GEMINI_API_KEY` and `OPENAI_API_KEY` set in your `.env` to run evaluations.

Before running for the first time, register the scorers:

```bash
uv run python scripts/register_scorers.py
```

Then run the evaluation against the 5-record sanity-check dataset (fast dry run):

```bash
uv run python scripts/run_evaluation.py
```

Or against the full 50-record dataset:

```bash
uv run python scripts/run_evaluation.py --dataset prompt-eval-v1
```

Results are logged to the MLflow experiment and saved to `evaluation_results.csv`. See [`docs/Milestone 13 - Whole MLFlow Implementation.md`](docs/Milestone%2013%20-%20Whole%20MLFlow%20Implementation.md) and [`docs/Milestone 14 - Evaluation Rate Limit Fix.md`](docs/Milestone%2014%20-%20Evaluation%20Rate%20Limit%20Fix.md) for full implementation details.
