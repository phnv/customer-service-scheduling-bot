# Changelog — Prompt System

All notable changes to the prompts, tool routing, and agent decision logic are documented in this file.

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
