# Prompt System Design & Strategy

Welcome to the prompt system for the **ClinicOps Customer Service Scheduling Bot**. This directory contains the system prompts, templates, configuration, and utilities that power our multi-agent architecture.

---

## 🏗️ Prompt Architecture & Composition

Our prompt system is designed around a **composed hierarchy**. Rather than using massive, monolithic prompts, each agent prompt is constructed dynamically by stitching together global guidelines and domain-specific roles.

```
                    ┌─────────────────────────┐
                    │      GLOBAL_PROMPT      │
                    │   (Global Persona, CSS, │
                    │   Error Recovery, Tone) │
                    └────────────┬────────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 ▼               ▼               ▼
         ┌──────────────┐┌──────────────┐┌──────────────┐
         │  RECEPTION   ││   BOOKING    ││     FAQ      │
         │    PROMPT    ││    PROMPT    ││    PROMPT    │
         └──────────────┘└──────────────┘└──────────────┘
```

At runtime, the LangGraph nodes call `render_prompt(GLOBAL_PROMPT + "\n\n" + AGENT_PROMPT, **variables)` to assemble the final instructions.

---

## 🔑 Key Engineering Strategies

### 1. Active Conversation Mode Retention (State-Aware Routing)
To solve the common problem of routing failures during mid-flow conversations (e.g., when a user responds with a short contextless answer like `"Cardiology"` or `"Next Tuesday"`), the **Coordinator** is state-aware.
* The coordinator node injects `{{ACTIVE_MODE_CONTEXT}}` derived from the active graph intent state (`state["intent"]`).
* If the user is mid-flow, the Coordinator LLM is instructed to prioritize routing to the active mode unless a clean context switch (like a specific FAQ question) is detected.

### 2. Explicit Terminology & State Alignments
Following our architecture evaluations, we strictly segregate the **Reservation** and **Appointment** concepts:
* **Reservation:** Temporary, unpaid slot hold generated via `reserve_slot_tool`. It has a strict expiration window.
* **Appointment:** Permanent, paid booking created automatically on the backend via a payment confirmation webhook event.
The Booking agent prompt is heavily optimized around this lifecycle so that it does not attempt to create appointments directly, but rather awaits and acknowledges `[System Event: Payment Confirmed]` updates.

### 3. Patient Selection & Mid-flow Switching
The Reception agent enforces contact identification first, then executes patient selection. It explicitly supports switching patients mid-turn (e.g., `"Actually, book it for my daughter instead"`) by looping through `find_patient_tool` and `select_patient_tool` to update the graph state seamlessly before handing off to Booking.

---

## 📁 File Structure

* [**`__init__.py`**](file:///wsl.localhost/Ubuntu/home/phen/projects/customer-service-scheduling-bot/app/prompts/__init__.py): Exposes prompts, render utilities, and variables configuration.
* [**`global_prompt.py`**](file:///wsl.localhost/Ubuntu/home/phen/projects/customer-service-scheduling-bot/app/prompts/global_prompt.py): Base behavior guidelines, error recovery, safety policies, and communication style.
* [**`coordinator.py`**](file:///wsl.localhost/Ubuntu/home/phen/projects/customer-service-scheduling-bot/app/prompts/coordinator.py): Prompt instructions for the intent classifier (Routes to Booking, FAQ, or Escalation).
* [**`reception.py`**](file:///wsl.localhost/Ubuntu/home/phen/projects/customer-service-scheduling-bot/app/prompts/reception.py): Rules for contact verification, new registration, and patient locking/switching.
* [**`booking.py`**](file:///wsl.localhost/Ubuntu/home/phen/projects/customer-service-scheduling-bot/app/prompts/booking.py): Appointment/Reservation lifecycle supervisor, availability queries, and slot reservations.
* [**`faq.py`**](file:///wsl.localhost/Ubuntu/home/phen/projects/customer-service-scheduling-bot/app/prompts/faq.py): RAG-backed clinic knowledge search rules.
* [**`escalation.py`**](file:///wsl.localhost/Ubuntu/home/phen/projects/customer-service-scheduling-bot/app/prompts/escalation.py): Static message returned to the user when routing to human support.
* [**`config.py`**](file:///wsl.localhost/Ubuntu/home/phen/projects/customer-service-scheduling-bot/app/prompts/config.py): Configuration dictionary defining template variables (e.g., `ORGANIZATION_NAME`, `TODAY`).
* [**`utils.py`**](file:///wsl.localhost/Ubuntu/home/phen/projects/customer-service-scheduling-bot/app/prompts/utils.py): Core template interpolation engine (`render_prompt`).

---

## ⚙️ Prompt Interpolation & Variables

Variables defined in `config.py` are enclosed in double curly brackets (e.g., `{{TODAY}}`, `{{ORGANIZATION_NAME}}`) and dynamically replaced by `render_prompt`. Do not write static dates or company names directly into prompt files; always use templates.
