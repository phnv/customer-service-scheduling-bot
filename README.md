# Customer Service Scheduling Bot

A multi-agent conversational customer service platform using a medical clinic as the demonstration domain.

## Overview

This project is a portfolio piece demonstrating AI engineering practices. It provides a complete simulation of a customer service workflow with a chat interface, acting as a clinic reception and scheduling assistant. 

It demonstrates:
- Multi-agent orchestration
- Agent routing
- Tool calling
- Semantic RAG (Retrieval-Augmented Generation) *(Upcoming)*
- Clean software architecture
- UI decoupling via ViewModels

The application is completely self-contained. All external service integrations (CRM, Payments, Availability) are mock implementations in the business logic layer.

## Architecture

The system uses **LangGraph** to coordinate between several specialized agents under a Supervisor pattern:
- **Coordinator Node:** Classifies user intent and routes the conversation.
- **Reception Agent:** Always runs before booking to identify or register the contact.
- **Booking Agent:** Uses tools to manage appointments and doctor availability.
- **FAQ Agent:** Uses RAG to answer questions based on clinic documentation.
- **Escalation Node:** Handles unsupported requests and human handoff.

The architecture is strictly layered:
`UI (Streamlit) -> Application (ViewModels) -> Agents (LangGraph) -> Tools (Wrappers) -> Services (Business Logic) -> Storage (SQLite/ChromaDB)`

## Tech Stack
- **Backend Framework:** LangGraph (Python)
- **LLM Provider:** Swappable (.env driven): Google Gemini (default), OpenAI, Anthropic
- **Database:** SQLite (managed via SQLModel)
- **Vector Store:** ChromaDB with `sentence-transformers`
- **Frontend:** Streamlit

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
