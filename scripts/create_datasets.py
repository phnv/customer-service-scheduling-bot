"""
Create MLflow evaluation datasets for agent evaluation.

Two datasets are created:
  1. sanity-check-5q  — 5 records, Correctness scorer only (no tool calls).
  2. prompt-eval-v1   — 50 records, all 4 scorers (Correctness, RelevanceToQuery,
                        ToolCallCorrectness, ToolCallEfficiency).

Schema (v1):
  inputs:
    user_message:        str   — the user's message (passed as kwarg to predict_fn)
    conversation_history: list — prior turns [{"role": ..., "content": ...}]

  expectations:
    expected_facts:      list[str]  — facts the agent response must contain (Correctness)
    expected_tool_calls: list[dict] — [{"name": "tool_name"}] or with "arguments" key
                                      (ToolCallCorrectness; omitted when no tool call expected)

  tags:
    agent_under_test: str  — metadata for filtering in MLflow UI (coordinator/reception/booking/faq)
    dataset_version:  str  — schema version tag

Usage:
    uv run python scripts/create_datasets.py             # create / merge (safe)
    uv run python scripts/create_datasets.py --purge     # delete & re-seed (use to fix bad data)

Versioning:
    DATASET_VERSION is stored as a tag on every record.
    The dataset NAME is kept stable so run_evaluation.py never needs updating.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import mlflow
from mlflow.genai.datasets import create_dataset, get_dataset

# ---------------------------------------------------------------------------
# Dataset versioning
# ---------------------------------------------------------------------------
# v1 = initial schema for the clean MLflow re-implementation (Milestone 10).
DATASET_VERSION = "v2" # 1st round of fixes + conversation history
DATASET_NAME = "prompt-eval-v2"
SANITY_DATASET_NAME = "sanity-check-5q-v2"

tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db")
mlflow.set_tracking_uri(tracking_uri)

experiment_id = os.getenv("MLFLOW_EXPERIMENT_ID")
if not experiment_id:
    print("ERROR: MLFLOW_EXPERIMENT_ID is not set.")
    sys.exit(1)


# =========================================================================
# DATASET 1: SANITY CHECK (5 RECORDS)
# Scorers: Correctness only — no tool call expectations.
# =========================================================================
SANITY_RECORDS = [
    {
        "inputs": {
            "user_message": "I'd like to book an appointment with Dr. Sarah Collins.",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": [
                "The agent asks for contact information.",
            ],
            "expected_intention": ["booking"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "sanity_001"},
    },
    {
        "inputs": {
            "user_message": "Hi, I'd like to book an appointment.",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": [
                "The agent proactively asks for contact information such as name and phone number or email.",
            ],
            "expected_intention": ["reception"],
        },
        "tags": {"agent_under_test": "reception", "index": "sanity_002"},
    },

    # Conversation history not being inputed 
    # - also should not test this here bcause envolves tool_calling
    {
        "inputs": {
            "user_message": "Do you have anything next Tuesday with a cardiologist?",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! I've selected you as the patient. How can I help you today?"},
            ],
        },
        "expectations": {
            "expected_facts": [
                "The agent checks availability for cardiology on next Tuesday.",
            ],
            "expected_intention": ["booking"],
        },
        "tags": {"agent_under_test": "booking", "index": "sanity_003"},
    },
    {
        "inputs": {
            "user_message": "What happens if I'm late to my appointment?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": [
                "The agent provides the clinic's lateness or cancellation policy.",
                # "Agent must complement with Cancellation Policy: Appointments must be cancelled at least 24 hours in advance to avoid a cancellation fee. Same-day cancellations may incur a fee of up to 50% of the consultation price",
            ],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "faq", "index": "sanity_004"},
    },


    # maybe NOT FIt for correctness scorer (escalation is right , escalation message must be improved)
    {
        "inputs": {
            "user_message": "This is ridiculous! I've been waiting for 3 hours. Let me speak to a manager right now!",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": [
                "The agent recognizes the user's frustration and stops trying to solve the issue automatically.",
                "The agent informs the user that the issue has been escalated to a human team.",
                "Chat session ends, no more messages from agent."
            ],
            "expected_intention": ["escalation"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "sanity_005"},
    },
]


# =========================================================================
# DATASET 2: FULL EVALUATION (50 RECORDS)
# Scorers: Correctness, RelevanceToQuery, ToolCallCorrectness, ToolCallEfficiency.
# expected_tool_calls is omitted for records where no tool call is expected.
# =========================================================================
FULL_RECORDS = [
    # ------------------------------------------------------------------
    # COORDINATOR AGENT RECORDS
    # ------------------------------------------------------------------
    {
        "inputs": {
            "user_message": "I'd like to book an appointment with Dr. Sarah Collins.",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent initiates the booking process and asks for the user's contact information."],
            "expected_intention": ["booking"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_001"},
    },
    {
        "inputs": {
            "user_message": "What are your clinic hours?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent provides the clinic's operating hours."],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_002"},
    },
    {
        "inputs": {
            "user_message": "This is ridiculous! I've been waiting for 3 hours. Let me speak to a manager right now!",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent apologizes and transfers the conversation to a human representative."],
            "expected_intention": ["escalation"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_003"},
    },
    {
        "inputs": {
            "user_message": "Cardiology.",
            "conversation_history": [
                {"role": "user", "content": "I need to see a doctor."},
                {"role": "assistant", "content": "Hello! Are you already registered with us? Could you share your full name and phone number so I can pull up your record?"},
                {"role": "user", "content": "My phone is +15550001234, I'm John Doe."},
                {"role": "assistant", "content": "Welcome back, John! What specialty are you looking for?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent continues the booking flow for the selected specialty."],
            "expected_intention": ["booking"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_004"},
    },

    # ~Duplicated - similar one on reception
    {
        "inputs": {
            "user_message": "Actually, how much does a dermatology consultation cost?",
            "conversation_history": [
                {"role": "user", "content": "I want to book an appointment."},
                {"role": "assistant", "content": "Sure! Are you already registered? Could you share your name and phone number?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The booking flow is preserved."],
            "expected_intention": ["faq"],
            "expected_tool_calls": [{"name": "search_services_tool"}],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_005"},
    },
    {
        "inputs": {
            "user_message": "I need to cancel my appointment for tomorrow.",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent asks for the user's contact information to locate and cancel the appointment."],
            "expected_intention": ["booking"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_006"},
    },

    # Duplicated row : similar on reception agent 
    {
        "inputs": {
            "user_message": "Actually, my phone number is wrong in your system — it should be 555-0199.",
            "conversation_history": [
                {"role": "user", "content": "Hi, I'm John Doe, phone +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! How can I help you today?"},
            ],
        },
        "expectations": {
            "expected_facts": ["Human takes over because data correction is not self-service."],
            "expected_intention": ["escalation"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_007"},
    },
    {
        "inputs": {
            "user_message": "Can I get my medical records sent to me?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent informs the user that this request requires human assistance and transfers them."],
            "expected_intention": ["escalation"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_008"},
    },
    {
        "inputs": {
            "user_message": "I want to change my primary care physician.",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent informs the user that changing physicians requires a human representative and initiates a transfer."],
            "expected_intention": ["escalation"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_009"},
    },
    {
        "inputs": {
            "user_message": "Who is the best doctor for back pain?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent provides information about doctors specializing in back pain or advises that it cannot provide medical recommendations."],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_010"},
    },
    {
        "inputs": {
            "user_message": "Can I pay my bill online?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent answers the question about online payments."],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_011"},
    },
    {
        "inputs": {
            "user_message": "Where are you located?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent provides the clinic's address and location details."],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_012"},
    },
    {
        "inputs": {
            "user_message": "I lost my prescription.",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent informs the user that a human representative is required for prescription issues and transfers them."],
            "expected_intention": ["escalation"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_013"},
    },
    {
        "inputs": {
            "user_message": "Is telehealth available?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent provides information on whether telehealth services are available."],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_014"},
    },
    {
        "inputs": {
            "user_message": "I want to complain about Dr. Smith.",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent apologizes and transfers the user to a human representative for complaints."],
            "expected_intention": ["escalation"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_015"},
    },
    {
        "inputs": {
            "user_message": "What is the parking situation?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent provides information about the parking situation at the clinic."],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "coordinator", "index": "full_016"},
    },

    # ------------------------------------------------------------------
    # RECEPTION AGENT RECORDS
    # ------------------------------------------------------------------
    {
        "inputs": {
            "user_message": "Hi, I'd like to book an appointment.",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent proactively asks for contact information such as name and phone or email."],
            "expected_intention": ["booking"],
        },
        "tags": {"agent_under_test": "reception", "index": "full_017"},
    },
    {
        "inputs": {
            "user_message": "My phone number is +15550001234 and I am John Doe.",
            "conversation_history": [
                {"role": "user", "content": "Hi, I'd like to book an appointment with Dr. Sarah Collins."},
                {"role": "assistant", "content": "Hello! Are you already registered with us? Could you share your full name and phone number (or email) so I can look up your record?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls the find_contact_tool to look up the contact."],
            "expected_intention": ["booking"],
            "expected_tool_calls": [{"name": "find_contact_tool"}],
        },
        "tags": {"agent_under_test": "reception", "index": "full_018"},
    },
    {
        "inputs": {
            "user_message": "My number is 555-9999, but I've never been there before.",
            "conversation_history": [
                {"role": "user", "content": "I need to book a session."},
                {"role": "assistant", "content": "Hello! Are you already registered? Could you share your name and phone number?"},
            ],
        },
        "expectations": {
            "expected_facts": [
                "The agent calls find_contact_tool to check if the contact exists.",
                "If not found, the agent asks for registration details.",
            ],
            "expected_intention": ["booking","reception"],
            "expected_tool_calls": [{"name": "find_contact_tool"}],
        },
        "tags": {"agent_under_test": "reception", "index": "full_019"},
    },
    {
        "inputs": {
            "user_message": "The appointment is for my daughter Emma.",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! I see you have two patients linked to your account: Lucas and Emma. Who is this appointment for?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls select_patient_tool with Emma's patient_id."],
            "expected_tool_calls": [{"name": "select_patient_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "reception", "index": "full_020"},
    },
    {
        "inputs": {
            "user_message": "Actually, can you book this for Lucas instead?",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! Who is this appointment for? I see Lucas and Emma."},
                {"role": "user", "content": "Emma."},
                {"role": "assistant", "content": "Got it, I've selected Emma. Shall we proceed with booking?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent switches the patient selection to Lucas."],
            "expected_tool_calls": [{"name": "select_patient_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "reception", "index": "full_021"},
    },
    {
        "inputs": {
            "user_message": "Actually, my phone number is wrong — it should be 555-0199.",
            "conversation_history": [
                {"role": "user", "content": "Hi, I'm John Doe, phone +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! How can I help you today?"},
            ],
        },
        "expectations": {
            "expected_facts": [
                "The agent does NOT call update_contact_tool.",
                "The agent escalates data corrections to a human agent.",
            ],
            "expected_intention": ["escalation"],
        },
        "tags": {"agent_under_test": "reception", "index": "full_022"},
    },
    {
        "inputs": {
            "user_message": "Hi.",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent proactively asks for contact identification."],
            "expected_intention": ["reception"],
        },
        "tags": {"agent_under_test": "reception", "index": "full_023"},
    },
    {
        "inputs": {
            "user_message": "I forgot my patient ID.",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent asks for alternative identifiers such as full name and phone or email."],
            "expected_tool_calls": [],
            "expected_intention": ["reception"],
        },
        "tags": {"agent_under_test": "reception", "index": "full_024"},
    },
    {
        "inputs": {
            "user_message": "My name is Jane Smith, +14443332222.",
            "conversation_history": [
                {"role": "user", "content": "I need to book a session."},
                {"role": "assistant", "content": "Hello! Are you already registered? Could you share your name and phone number?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls find_contact_tool with the provided phone number."],
            "expected_tool_calls": [{"name": "find_contact_tool"}],
            "expected_intention": ["reception"],
        },
        "tags": {"agent_under_test": "reception", "index": "full_025"},
    },

    # useless edge case? reevaluate this row
    {
        "inputs": {
            "user_message": "I don't have a phone number.",
            "conversation_history": [
                {"role": "user", "content": "I need to book a session."},
                {"role": "assistant", "content": "Hello! Are you already registered? Could you share your name and phone number?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent asks for an email address or another identifier to look up the contact."],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "reception", "index": "full_026"},
    },
    {
        "inputs": {
            "user_message": "It's for my son, Michael.",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +14443332222."},
                {"role": "assistant", "content": "Welcome back, Jane! I see you have one patient linked to your account: Michael. Who is this appointment for?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls select_patient_tool with Michael's patient_id."],
            "expected_tool_calls": [{"name": "select_patient_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "reception", "index": "full_027"},
    },

    # useless edge case? reevaluate this row
    {
        "inputs": {
            "user_message": "Wait, I need to update my email address.",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +14443332222."},
                {"role": "assistant", "content": "Welcome back, Jane!"},
            ],
        },
        "expectations": {
            "expected_facts": [
                "The agent escalates to a human agent.",
                "Self-service data corrections are not allowed.",
            ],
            "expected_intention": ["escalation"],
        },
        "tags": {"agent_under_test": "reception", "index": "full_028"},
    },

    # ------------------------------------------------------------------
    # BOOKING AGENT RECORDS
    # ------------------------------------------------------------------
    {
        "inputs": {
            "user_message": "Do you have anything next Tuesday with a cardiologist?",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! I've selected you as the patient. How can I help you today?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls check_availability_tool for cardiology on next Tuesday."],
            "expected_tool_calls": [{"name": "check_availability_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_029"},
    },
    {
        "inputs": {
            # Must enhance conversation history with contact info
            "user_message": "The 10am slot with Dr. Silva works.",
            "conversation_history": [
                {"role": "user", "content": "Do you have anything next Tuesday with a cardiologist?"},
                {"role": "assistant", "content": "Here are the available cardiology slots for next Tuesday:\n- Dr. Silva at 10:00 AM\n- Dr. Silva at 14:30\n- Dr. Brooks at 11:00 AM"},
            ],
        },
        "expectations": {
            "expected_facts": [
                "The agent asks for explicit user confirmation before calling reserve_slot_tool.",
                "The agent does NOT reserve the slot without confirmation.",
            ],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_030"},
    },

    # weird conversation, needs better wording 
    {
        "inputs": {
            "user_message": "Yes, please book it.",
            "conversation_history": [
                {"role": "user", "content": "The 10am slot with Dr. Silva works."},
                {"role": "assistant", "content": "To confirm — you'd like the 10:00 AM slot with Dr. Silva on Tuesday. Is that correct?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls reserve_slot_tool to confirm the booking."],
            "expected_tool_calls": [{"name": "reserve_slot_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_031"},
    },
    {
        "inputs": {
            "user_message": "I need to cancel my appointment for tomorrow.",
            "conversation_history": [
                {"role": "user", "content": "Hi, +15550001234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls cancel_appointment_tool."],
            "expected_tool_calls": [{"name": "cancel_appointment_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_032"},
    },
    {
        "inputs": {
            "user_message": "I need to reschedule my Thursday appointment to next week.",
            "conversation_history": [
                {"role": "user", "content": "Hi, +15550001234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls reschedule_appointment_tool."],
            "expected_tool_calls": [{"name": "reschedule_appointment_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_033"},
    },
    {
        "inputs": {
            "user_message": "I need an endocrinologist.",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help you today?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls check_availability_tool for endocrinology."],
            "expected_tool_calls": [{"name": "check_availability_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_034"},
    },
    {
        "inputs": {
            "user_message": "[System Event: Payment Confirmed]",
            "conversation_history": [
                {"role": "user", "content": "Yes, please book the 10am slot."},
                {"role": "assistant", "content": "I've reserved the 10:00 AM slot with Dr. Silva. A payment link will be generated shortly. The slot is held temporarily."},
            ],
        },
        "expectations": {
            "expected_facts": [
                "The agent acknowledges the confirmed payment.",
                "The agent does NOT call any tools in response to the payment event.",
            ],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_035"},
    },
    {
        "inputs": {
            "user_message": "Do you have any availability for a general checkup this Friday?",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! I've selected you as the patient. How can I help you today?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls check_availability_tool for a general checkup on Friday."],
            "expected_tool_calls": [{"name": "check_availability_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_036"},
    },
    {
        "inputs": {
            "user_message": "I want the 9am slot with Dr. Adams.",
            "conversation_history": [
                {"role": "user", "content": "Do you have anything this Friday for a checkup?"},
                {"role": "assistant", "content": "Here are the available slots for Friday:\n- Dr. Adams at 09:00 AM\n- Dr. Adams at 14:00\n- Dr. Evans at 11:30 AM"},
            ],
        },
        "expectations": {
            "expected_facts": [
                "The agent asks for explicit confirmation of the 9am slot with Dr. Adams before booking.",
            ],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_037"},
    },
    {
        "inputs": {
            "user_message": "Yes, that's correct.",
            "conversation_history": [
                {"role": "user", "content": "I want the 9am slot with Dr. Adams."},
                {"role": "assistant", "content": "To confirm — you'd like the 09:00 AM slot with Dr. Adams on Friday. Is that correct?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls reserve_slot_tool to book the 9am slot."],
            "expected_tool_calls": [{"name": "reserve_slot_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_038"},
    },
    {
        "inputs": {
            "user_message": "I want to cancel my reservation with Dr. Adams.",
            "conversation_history": [
                {"role": "user", "content": "Hi, +15550001234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls cancel_appointment_tool or cancel_reservation_tool."],
            "expected_tool_calls": [{"name": "cancel_appointment_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_039"},
    },
    {
        "inputs": {
            "user_message": "Can I reschedule my appointment with Dr. Silva to tomorrow?",
            "conversation_history": [
                {"role": "user", "content": "Hi, +15550001234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help?"},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent calls reschedule_appointment_tool."],
            "expected_tool_calls": [{"name": "reschedule_appointment_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_040"},
    },
    {
        "inputs": {
            "user_message": "[System Event: Payment Expired]",
            "conversation_history": [
                {"role": "user", "content": "Yes, please book the 10am slot."},
                {"role": "assistant", "content": "I've reserved the 10:00 AM slot with Dr. Silva. A payment link will be generated shortly. The slot is held temporarily."},
            ],
        },
        "expectations": {
            "expected_facts": [
                "The agent acknowledges that the payment expired and the reservation was released.",
                "The agent asks if the user wants to book again.",
            ],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "booking", "index": "full_041"},
    },

    # ------------------------------------------------------------------
    # FAQ AGENT RECORDS
    # ------------------------------------------------------------------
    {
        "inputs": {
            "user_message": "What happens if I'm late to my appointment?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent searches the knowledge base and retrieves the lateness or cancellation policy."],
            "expected_tool_calls": [{"name": "search_faq_tool"}],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "faq", "index": "full_042"},
    },
    {
        "inputs": {
            "user_message": "Do you accept Blue Cross insurance?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent searches the knowledge base for insurance acceptance information."],
            "expected_tool_calls": [{"name": "search_faq_tool"}],
            "expected_intention": ["booking","reception"],
        },
        "tags": {"agent_under_test": "faq", "index": "full_043"},
    },
    {
        "inputs": {
            "user_message": "What specialties do you offer?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["The agent searches the knowledge base for available specialties."],
            "expected_tool_calls": [{"name": "search_faq_tool"}],
            "expected_intention": ["faq","reception"],
        },
        "tags": {"agent_under_test": "faq", "index": "full_044"},
    },
    #~Duplicated row -  similar one testing coordinator
    {
        "inputs": {
            "user_message": "How much does a dermatology consultation cost?",
            "conversation_history": [
                {"role": "user", "content": "I want to book a cardiology appointment."},
                {"role": "assistant", "content": "Sure! Are you registered? Please share your name and phone number."},
            ],
        },
        "expectations": {
            "expected_facts": ["The agent retrieves dermatology consultation cost information."],
            "expected_tool_calls": [{"name": "search_services_tool"}],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "faq", "index": "full_045"},
    },
    {
        "inputs": {
            "user_message": "Can I book an appointment for tomorrow?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": [
                "The agent handles the booking request or directs the user to the booking flow.",
                "The agent does not refuse the booking request.",
            ],
            "expected_intention": ["booking"]
        },
        "tags": {"agent_under_test": "faq", "index": "full_046"},
    },
    {
        "inputs": {
            "user_message": "I have a headache, what medicine should I take?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": [
                "The agent does NOT provide medical advice.",
                "The agent recommends consulting a doctor.",
            ],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "faq", "index": "full_047"},
    },
    {
        "inputs": {
            "user_message": "Do you accept Medicare?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": ["Agent presents Medicare acceptance information."],
            "expected_tool_calls": [{"name": "search_faq_tool"}],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "faq", "index": "full_048"},
    },
    {
        "inputs": {
            "user_message": "What should I do if my arm hurts?",
            "conversation_history": [],
        },
        "expectations": {
            "expected_facts": [
                "The agent does NOT provide medical advice.",
                "The agent recommends consulting a doctor or calling emergency services.",
            ],
            "expected_intention": ["faq"],
        },
        "tags": {"agent_under_test": "faq", "index": "full_049"},
    },
]


# =========================================================================
# Dataset creation logic
# =========================================================================

def _attach_version_tag(records: list[dict]) -> list[dict]:
    """Inject dataset_version into each record's tags."""
    tagged = []
    for r in records:
        tags = {**r.get("tags", {}), "dataset_version": DATASET_VERSION}
        tagged.append({**r, "tags": tags})
    return tagged


def _write_dataset_config() -> None:
    """Write scripts/dataset_config.json with current dataset names and version.

    Called at the end of every successful dataset creation run so that
    run_evaluation.py always reads the authoritative names from a single
    JSON file rather than hardcoding them.
    """
    config = {
        "version": DATASET_VERSION,
        "datasets": {
            "sanity": {
                "name": SANITY_DATASET_NAME,
                "description": "5-record sanity check \u2014 Correctness scorer only",
            },
            "full": {
                "name": DATASET_NAME,
                "description": "50-record full evaluation \u2014 all 4 scorers",
            },
        },
    }
    config_path = Path(__file__).parent / "dataset_config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  dataset_config.json updated → {config_path}")


def generate_dataset(name: str, records: list[dict], purge: bool = False) -> None:
    """Create or update a single named MLflow evaluation dataset."""
    records = _attach_version_tag(records)
    try:
        dataset = get_dataset(name=name)
        if purge:
            df = dataset.to_df()
            existing_ids = df["dataset_record_id"].tolist()
            if existing_ids:
                deleted = dataset.delete_records(existing_ids)
                print(f"  Purged {deleted} existing record(s) from '{name}'.")
            else:
                print(f"  Dataset '{name}' exists but has no records to purge.")
        else:
            print(f"  Dataset '{name}' already exists — merging {len(records)} record(s)...")
    except Exception:
        print(f"  Creating dataset '{name}'...")
        dataset = create_dataset(name=name, experiment_id=[experiment_id])

    dataset.merge_records(records)
    print(f"  Dataset '{name}' now has {len(dataset.to_df())} record(s) (version={DATASET_VERSION}).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create MLflow evaluation datasets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  Create / merge (safe, default):\n"
            "    uv run python scripts/create_datasets.py\n\n"
            "  Purge existing records and re-seed (use to fix bad data):\n"
            "    uv run python scripts/create_datasets.py --purge\n"
        ),
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        default=False,
        help=(
            "Delete all existing records before inserting. "
            "Use this to correct datasets seeded with incorrect data. "
            "Not recommended as a routine operation — omit for normal updates."
        ),
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Creating Evaluation Datasets")
    print(f"  version : {DATASET_VERSION}")
    print(f"  purge   : {args.purge}")
    print("=" * 60)
    generate_dataset(SANITY_DATASET_NAME, SANITY_RECORDS, purge=args.purge)
    generate_dataset(DATASET_NAME, FULL_RECORDS, purge=args.purge)
    _write_dataset_config()
    print("=" * 60)
    print("Done. Run manually and verify in MLflow UI.")
    print("=" * 60)
