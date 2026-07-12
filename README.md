# Customer Service Scheduling Bot

A multi-agent conversational customer service platform using a medical clinic as the demonstration domain.

## Overview

This project is a portfolio piece demonstrating AI engineering practices. It provides a complete simulation of a customer service workflow with a chat interface, acting as a clinic reception and scheduling assistant. 

It demonstrates:
- Multi-agent orchestration
- Agent routing
- Tool calling
- Semantic RAG (Retrieval-Augmented Generation)
- Clean software architecture

The application is completely self-contained. All external service integrations (CRM, Payments, Availability) are mock implementations.

## Architecture

The system uses **LangGraph** to coordinate between several specialized agents:
- **Coordinator Agent:** Handles initial reception duties and routes the conversation.
- **Booking Agent:** Uses tools to manage appointments and doctor availability.
- **FAQ Agent:** Uses RAG to answer questions based on clinic documentation.
- **Escalation Agent:** Handles unsupported requests and human handoff.

The architecture is strictly layered:
`UI (Streamlit) -> Agents (LangGraph) -> Tools (Wrappers) -> Services (Business Logic) -> Storage (SQLite/ChromaDB)`

## Tech Stack
- **Backend Framework:** LangGraph (Python)
- **Database:** SQLite (managed via SQLModel)
- **Vector Store:** ChromaDB with `sentence-transformers`
- **Frontend:** Streamlit

## Getting Started

*(Instructions will be added as implementation progresses in future milestones)*
