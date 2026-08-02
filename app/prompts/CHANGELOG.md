# Changelog — Prompt System

All notable changes to the prompts, tool routing, and agent decision logic are documented in this file.

---

## [3.1.0] - 2026-08-02 — Milestone 11: Prompt Evaluation Turn #1

### Added
* **System Event Routing Rule (Coordinator)**: Added an explicit rule to `coordinator.py` (v2.2.0) prepended at the top of `# Decision Rules — intent`: any message matching `[System Event: ...]` is always routed to `intent="booking"`. Two few-shot examples reinforce the rule for Payment Confirmed and Payment Expired events.
* **Escalation Protocol (Global)**: Added `# Escalation Protocol` section to `global_prompt.py` applying universally to all agents. Before escalating, agents must: (1) apologise sincerely, (2) ask for the user's full name and phone number if not already in context, (3) record contact details and reason in `conversation_summary`, then (4) proceed with the handoff. Includes two few-shot examples (complaint and frustration cases).

### Changed
* **Payment Confirmed Response (Booking)**: Updated `booking.py` (v2.1.0) — agent now presents full appointment details (doctor, date, time, specialty if available), follows with "Is there anything else I can help you with today?", and wishes the user well if no further help is needed.
* **Payment Expired Response (Booking)**: Updated `booking.py` — agent now apologises sincerely before delivering the expiry news, then proactively offers to search for a new slot with an open-ended question.
* **Dataset v2 → v3** (`create_datasets.py`): Bumped `DATASET_VERSION` to `v3` (datasets: `prompt-eval-v3`, `sanity-check-5q-v3`). Updated `expected_facts` in 7 existing records (`full_035`, `full_041`, `full_003`, `full_007`, `full_008`, `full_013`, `full_015`) to reflect new prompt behaviours. Added 2 new escalation-protocol records (`full_050` booking, `full_051` reception). Total: 52 records (was 50).

---

## [3.0.0] - 2026-07-23 — Milestone 12: Prompt Evaluation #1

### Added
* **Unified Persona Rule (Global)**: Added `# Persona` section to `global_prompt.py` enforcing that all non-escalation agents present as a single unified assistant. Agents must never reference internal agent names, team names, or imply a handoff. The only legitimate handoff is human escalation.
* **Proactive Contact Identification (Reception)**: Added Responsibility 0 to `reception.py` (v3.0.0) requiring Reception to greet the user and ask for their name and identifier (phone/email/document) on the very first turn of every conversation, before any intent is expressed.
* **Escalation on Contact Correction (Reception)**: Added explicit rule and few-shot example to `reception.py`: if the user reports that any stored contact field is incorrect, Reception must immediately route to human escalation. The agent must not attempt to update the record.
* **Pricing Tool for FAQ (FAQ)**: Added `search_services_tool(specialty, service_type, service_mode)` to `faq.py` (v2.0.0) for live pricing queries against the services catalogue. Decision rules now route by question type: pricing → `search_services_tool`, all other clinic questions → `search_faq_tool`.
* **Proactive Booking Resume (FAQ)**: Added rule to `faq.py`: after answering a pricing question mid-booking flow, the agent proactively offers to resume the booking.

### Changed
* **Reception v3.0.0**: Full rewrite of `reception.py`. Version bumped from 2.0.0 → 3.0.0.
* **FAQ v2.0.0**: Full rewrite of `faq.py`. Version bumped from 1.0.0 → 2.0.0.
* **Escalation message** (`escalation.py`): Message tightened to be trigger-agnostic, covering both frustration-based and data-correction-based escalations.

### Removed
* **`update_contact_tool` (Reception)**: Removed from `reception.py` Responsibilities, Available Tools list, and few-shot examples. Contact data correction is now exclusively an escalation trigger. The underlying service method is preserved in `app/services/` for programmatic use but must not be bound to any agent.
* **`BOOKING_TEAM_NAME` (Config)**: Removed from `config.py` entirely. All prompt references to a named scheduling team have been replaced with direct handling or unified-persona language. The variable no longer exists and must not be reintroduced.

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
