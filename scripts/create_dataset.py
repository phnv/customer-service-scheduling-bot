"""
Create the MLflow evaluation dataset for prompt evaluation.

This script creates a multi-turn evaluation dataset covering all 4 active agents:
Coordinator, Reception, Booking, and FAQ.

Usage:
    uv run python scripts/create_dataset.py
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

import mlflow
from mlflow.genai.datasets import create_dataset

# ---------------------------------------------------------------------------
# MLflow Configuration
# ---------------------------------------------------------------------------
tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
mlflow.set_tracking_uri(tracking_uri)

experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "customer-service-bot")
mlflow.set_experiment(experiment_name)

DATASET_NAME = "prompt-eval-v1"

# ---------------------------------------------------------------------------
# Evaluation Records (Multi-turn)
#
# Schema:
#   inputs.user_message:          str — the current user turn
#   inputs.conversation_history:  list[dict] — prior turns [{role, content}, ...]
#   inputs.agent_under_test:      str — which agent is being primarily evaluated
#   expected_response:            str — description of what a correct response looks like
# ---------------------------------------------------------------------------

RECORDS = [
    # =========================================================================
    # COORDINATOR (6 records) — Intent classification and routing
    # =========================================================================
    {
        "inputs": {
            "user_message": "I'd like to book an appointment with Dr. Sarah Collins.",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expected_response": "Routes to booking intent. The coordinator should classify this as a scheduling request and output {\"intent\": \"booking\"}.",
    },
    {
        "inputs": {
            "user_message": "What are your clinic hours?",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expected_response": "Routes to faq intent. This is a general knowledge question about the clinic and should output {\"intent\": \"faq\"}.",
    },
    {
        "inputs": {
            "user_message": "This is ridiculous! I've been waiting for 3 hours. Let me speak to a manager right now!",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expected_response": "Routes to escalation intent. Strong frustration and complaint language should trigger {\"intent\": \"escalation\"}.",
    },
    {
        "inputs": {
            "user_message": "Cardiology.",
            "conversation_history": [
                {"role": "user", "content": "I need to see a doctor."},
                {"role": "assistant", "content": "I'd be happy to help you book an appointment! Could you please provide your phone number or email so I can look up your record?"},
                {"role": "user", "content": "My phone is 555-1234, I'm John Doe."},
                {"role": "assistant", "content": "Welcome back, John! What specialty are you looking for?"},
            ],
            "agent_under_test": "coordinator",
        },
        "expected_response": "Routes to booking intent. Mid-flow response answering the agent's question about specialty should continue the active booking mode.",
    },
    {
        "inputs": {
            "user_message": "Actually, how much does a dermatology consultation cost?",
            "conversation_history": [
                {"role": "user", "content": "I want to book an appointment."},
                {"role": "assistant", "content": "Sure! Could you provide your phone number or email?"},
            ],
            "agent_under_test": "coordinator",
        },
        "expected_response": "Routes to faq intent. Even during a booking flow, a pricing question should be routed to FAQ.",
    },
    {
        "inputs": {
            "user_message": "I need to cancel my appointment for tomorrow.",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expected_response": "Routes to booking intent. Cancellation is a scheduling action handled by the booking agent.",
    },

    # =========================================================================
    # RECEPTION (5 records) — Contact identification and patient selection
    # =========================================================================
    {
        "inputs": {
            "user_message": "Hi, I'd like to book an appointment.",
            "conversation_history": [],
            "agent_under_test": "reception",
        },
        "expected_response": "Asks for contact information (phone, email, or document). Should NOT check availability or mention doctors yet. Must identify the contact first.",
    },
    {
        "inputs": {
            "user_message": "My phone number is 555-1234 and I am John Doe.",
            "conversation_history": [
                {"role": "user", "content": "Hi, I'd like to book an appointment with Dr. Sarah Collins."},
                {"role": "assistant", "content": "Hello! Could you please provide your phone number or email address so I can look up your record?"},
            ],
            "agent_under_test": "reception",
        },
        "expected_response": "Calls find_contact_tool with phone 555-1234. Should identify the existing contact and their linked patients. If single patient, auto-selects via select_patient_tool.",
    },
    {
        "inputs": {
            "user_message": "My number is 555-9999, but I've never been there before.",
            "conversation_history": [
                {"role": "user", "content": "I need to book a session."},
                {"role": "assistant", "content": "Sure, please provide your phone number or email."},
            ],
            "agent_under_test": "reception",
        },
        "expected_response": "Calls find_contact_tool first. When not found, should ask for full name, email, and birthdate to register as a new contact. Should NOT say 'Welcome back'.",
    },
    {
        "inputs": {
            "user_message": "The appointment is for my daughter Emma.",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is 555-1234."},
                {"role": "assistant", "content": "Welcome back, John! I see you have two patients linked to your account: Lucas and Emma. Who is this appointment for?"},
            ],
            "agent_under_test": "reception",
        },
        "expected_response": "Calls select_patient_tool with Emma's patient_id. Should confirm the patient selection and indicate readiness to proceed to scheduling.",
    },
    {
        "inputs": {
            "user_message": "Actually, can you book this for Lucas instead?",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is 555-1234."},
                {"role": "assistant", "content": "Welcome back! Who is this appointment for? I see Lucas and Emma."},
                {"role": "user", "content": "Emma."},
                {"role": "assistant", "content": "Got it, I've selected Emma. Shall we proceed with booking?"},
            ],
            "agent_under_test": "reception",
        },
        "expected_response": "Handles patient switching. Should call find_patient_tool for Lucas, then select_patient_tool to update the selection. Confirms the switch before proceeding.",
    },

    # =========================================================================
    # BOOKING (7 records) — Availability, reservation, cancellation, rescheduling
    # =========================================================================
    {
        "inputs": {
            "user_message": "Do you have anything next Tuesday with a cardiologist?",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is 555-1234."},
                {"role": "assistant", "content": "Welcome back, John! I've selected you as the patient. How can I help you today?"},
            ],
            "agent_under_test": "booking",
        },
        "expected_response": "Calls check_availability_tool with specialty='cardiology' and start_date for next Tuesday. Should present available slots clearly.",
    },
    {
        "inputs": {
            "user_message": "The 10am slot with Dr. Silva works.",
            "conversation_history": [
                {"role": "user", "content": "Do you have anything next Tuesday with a cardiologist?"},
                {"role": "assistant", "content": "Here are the available cardiology slots for next Tuesday:\n- Dr. Silva at 10:00 AM\n- Dr. Silva at 14:30\n- Dr. Brooks at 11:00 AM"},
            ],
            "agent_under_test": "booking",
        },
        "expected_response": "Should confirm slot details (doctor, date, time, specialty) BEFORE calling reserve_slot_tool. Asks for explicit confirmation.",
    },
    {
        "inputs": {
            "user_message": "Yes, please book it.",
            "conversation_history": [
                {"role": "user", "content": "The 10am slot with Dr. Silva works."},
                {"role": "assistant", "content": "To confirm — you'd like the 10:00 AM slot with Dr. Silva on Tuesday. Is that correct?"},
            ],
            "agent_under_test": "booking",
        },
        "expected_response": "Calls reserve_slot_tool with the slot_id and conversation_id. Informs the user that a payment link will be provided and the slot is held temporarily.",
    },
    {
        "inputs": {
            "user_message": "I need to cancel my appointment for tomorrow.",
            "conversation_history": [
                {"role": "user", "content": "Hi, 555-1234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help?"},
            ],
            "agent_under_test": "booking",
        },
        "expected_response": "Calls cancel_appointment_tool with the appointment_id. Should confirm the cancellation and inform the user the slot has been released.",
    },
    {
        "inputs": {
            "user_message": "I need to reschedule my Thursday appointment to next week.",
            "conversation_history": [
                {"role": "user", "content": "Hi, 555-1234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help?"},
            ],
            "agent_under_test": "booking",
        },
        "expected_response": "Should use reschedule_appointment_tool or cancel + re-reserve flow. Should check availability for next week before proceeding.",
    },
    {
        "inputs": {
            "user_message": "I need an endocrinologist.",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is 555-1234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help you today?"},
            ],
            "agent_under_test": "booking",
        },
        "expected_response": "Calls check_availability_tool with specialty='endocrinology'. Should present available doctors and their slots. Must NOT provide medical advice.",
    },
    {
        "inputs": {
            "user_message": "[System Event: Payment Confirmed]",
            "conversation_history": [
                {"role": "user", "content": "Yes, please book the 10am slot."},
                {"role": "assistant", "content": "I've reserved the 10:00 AM slot with Dr. Silva. A payment link will be generated shortly. The slot is held temporarily."},
            ],
            "agent_under_test": "booking",
        },
        "expected_response": "Acknowledges the payment confirmation warmly. Confirms appointment details (doctor, date, time). Does NOT call any tool — the backend already handled the appointment creation.",
    },

    # =========================================================================
    # FAQ (5 records) — Knowledge retrieval, grounded answers, domain boundaries
    # =========================================================================
    {
        "inputs": {
            "user_message": "What happens if I'm late to my appointment?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expected_response": "Calls search_faq_tool to retrieve the lateness/cancellation policy. Provides a grounded answer based on retrieved content. Should NOT mention booking or scheduling.",
    },
    {
        "inputs": {
            "user_message": "Do you accept Blue Cross insurance?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expected_response": "Calls search_faq_tool to search for insurance information. Provides answer based on retrieved knowledge base content.",
    },
    {
        "inputs": {
            "user_message": "What specialties do you offer?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expected_response": "Calls search_faq_tool to retrieve specialties information. Lists available specialties based on knowledge base content. Should NOT offer to book.",
    },
    {
        "inputs": {
            "user_message": "Can I book an appointment for tomorrow?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expected_response": "Recognizes this is a booking request, not an FAQ question. Should redirect the user to the scheduling team. Must NOT attempt to book or check availability.",
    },
    {
        "inputs": {
            "user_message": "I have a headache, what medicine should I take?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expected_response": "Does NOT provide medical advice. Should politely decline and explain the clinic cannot diagnose or prescribe medication. May suggest consulting a doctor.",
    },
]


def main():
    print(f"Creating dataset '{DATASET_NAME}' with {len(RECORDS)} records...")

    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        print(f"ERROR: Experiment '{experiment_name}' not found.")
        sys.exit(1)

    experiment_id = experiment.experiment_id
    print(f"Using experiment: {experiment_name} (ID: {experiment_id})")

    # Create the dataset
    dataset = create_dataset(
        name=DATASET_NAME,
        experiment_id=experiment_id,
    )

    # Add records
    dataset.merge_records(RECORDS)

    # Verify
    df = dataset.to_df()
    print(f"\nDataset created successfully!")
    print(f"  Name: {DATASET_NAME}")
    print(f"  Records: {len(df)}")
    print(f"  Columns: {list(df.columns)}")

    # Show breakdown by agent
    agents = {}
    for record in RECORDS:
        agent = record["inputs"]["agent_under_test"]
        agents[agent] = agents.get(agent, 0) + 1

    print(f"\n  Records per agent:")
    for agent, count in sorted(agents.items()):
        print(f"    {agent}: {count}")


if __name__ == "__main__":
    main()
