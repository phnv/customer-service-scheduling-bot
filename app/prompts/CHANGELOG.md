# Changelog — Prompt System

All notable changes to the prompts, tool routing, and agent decision logic are documented in this file.

---

## [2.1.0] - 2026-07-22

### Added
* **Durable Flow Tracking (Coordinator)**: Updated output JSON schema (`intent`, `flow`, `conversation_summary`) in `coordinator.py` to distinguish per-turn routing (`intent`) from multi-turn task context (`flow`), allowing single-turn FAQ detours without abandoning active flows.
* **Conversation Summary Maintenance (Coordinator)**: Added instructions and guidelines in `coordinator.py` for generating and maintaining a rolling third-person conversation summary on key milestone events.
* **Contact Details Update Support (Reception)**: Added `update_contact_tool` specification, decision rules, and few-shot example in `reception.py` for correcting stored contact information (phone, email, name, birthdate).
* **Explicit Tool Query Parameter (FAQ)**: Documented parameter `query` for `search_faq_tool` in `faq.py`.
* **Pre-Payment Rescheduling (Booking)**: Added explicit instructions to `booking.py` on how to reschedule an active reservation before payment by cancelling and re-reserving.

### Changed
* **Single-Step Rescheduling (Booking)**: Updated `booking.py` prompt instructions to handle rescheduling directly via `reschedule_appointment_tool` in a single step.
* **Direct Booking Routing (Coordinator)**: Updated LangGraph routing logic in `coordinator.py` to bypass the Reception agent entirely and route directly to Booking when the user's `contact_id` and `patient_id` are already established in state.
* **Prompt Cleanups**: Removed language implying Reception controls routing in `reception.py`. Clarified ID injection nullability in `booking.py`.

### Removed
* **Lead Tracking Tool (Booking)**: Removed `update_lead_tool` tool definition and post-booking update instructions from `booking.py`.

---

## [2.0.0] - 2026-07-16

### Added
* **Active Mode Retention (Coordinator)**: Introduced the `{{ACTIVE_MODE_CONTEXT}}` template parameter in `coordinator.py` to allow context-aware intent routing. The coordinator now receives details about the active conversation mode (e.g. `booking` or `faq`) to prevent misrouting on short continuation messages (e.g. "Cardiology").
* **Patient Switching Support (Reception)**: Explicit rules added to `reception.py` directing the agent on how to handle mid-conversation patient swaps. The agent is instructed to look up the new name using `find_patient_tool` and override the state by calling `select_patient_tool` again.
* **Payment Hook System Events (Booking)**: Instructed `booking.py` on how to respond to injected system messages `[System Event: Payment Confirmed]` and `[System Event: Payment Expired]`.
* **Tool Failure Resilience (Booking)**: Added few-shot examples and decision paths in `booking.py` instructing the agent to attempt retries or escalate if `check_availability_tool` fails.
* **Pre-Payment Cancellations**: Bound `cancel_reservation_tool` to the `Booking` agent tools so it can release temporary slots before payment is completed.

### Changed
* **Terminology Alignment**: Strictly separated **Reservation** (temporary, unpaid slot hold) from **Appointment** (permanent, paid confirmation) in `booking.py`. Removed references to the agent creating appointments directly (since this is handled by backend webhook triggers).
* **Tool List Corrections**:
  * Corrected `cancel_appointment_tool` description in `booking.py` prompts to limit it strictly to paid, confirmed appointments.
  * Added descriptions for `find_patient_tool` and `create_patient_tool` inside `reception.py` to ensure accurate tool invocation parameters.

---

## [1.0.0] - 2026-07-10

### Added
* Initial multi-agent prompt system setup with composition (`GLOBAL_PROMPT` + agent prompt).
* Basic intent routing coordinator (`coordinator.py`).
* Identity validation reception prompt (`reception.py`).
* General booking and rescheduling logic (`booking.py`).
* Simple keyword RAG prompt rules (`faq.py`).
