"""
Create MLflow evaluation datasets for prompt evaluation.

Usage:
    uv run python scripts/create_datasets.py             # create / merge (safe)
    uv run python scripts/create_datasets.py --purge     # delete & re-seed (use to fix bad data)

Versioning:
    Dataset records are tagged with {"dataset_version": DATASET_VERSION}.
    Bump DATASET_VERSION when introducing breaking schema changes. The dataset
    NAME is intentionally kept stable so run_evaluation.py never needs updating.
"""

import argparse
import os
import sys
from dotenv import load_dotenv

load_dotenv()

import mlflow
from mlflow.genai.datasets import create_dataset, get_dataset

# ---------------------------------------------------------------------------
# Dataset versioning
# ---------------------------------------------------------------------------
# Bump this constant when the record schema changes in a breaking way.
# The version is stored as a tag on every record (not encoded in the dataset name).
DATASET_VERSION = "v1"

tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db")
mlflow.set_tracking_uri(tracking_uri)

experiment_id = os.getenv("MLFLOW_EXPERIMENT_ID")
if not experiment_id:
    print("ERROR: MLFLOW_EXPERIMENT_ID is not set.")
    sys.exit(1)

# =========================================================================
# PHASE A: SANITY CHECK (5 RECORDS)
# =========================================================================
SANITY_RECORDS = [
    {
        "inputs": {
            "user_message": "I'd like to book an appointment with Dr. Sarah Collins.",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to booking intent.",
    },
    {
        "inputs": {
            "user_message": "Hi, I'd like to book an appointment.",
            "conversation_history": [],
            "agent_under_test": "reception",
        },
        "expectations": "Proactively asks for contact information (name and phone/email).",
    },
    {
        "inputs": {
            "user_message": "Do you have anything next Tuesday with a cardiologist?",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! I've selected you as the patient. How can I help you today?"},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Calls check_availability_tool.",
    },
    {
        "inputs": {
            "user_message": "What happens if I'm late to my appointment?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expectations": "Retrieves lateness/cancellation policy.",
    },
    {
        "inputs": {
            "user_message": "This is ridiculous! I've been waiting for 3 hours. Let me speak to a manager right now!",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to escalation intent.",
    },
]

# =========================================================================
# ORIGINAL 27 RECORDS
# =========================================================================
ORIGINAL_27_RECORDS = [
    {
        "inputs": {
            "user_message": "I'd like to book an appointment with Dr. Sarah Collins.",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to booking intent.",
    },
    {
        "inputs": {
            "user_message": "What are your clinic hours?",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to faq intent.",
    },
    {
        "inputs": {
            "user_message": "This is ridiculous! I've been waiting for 3 hours. Let me speak to a manager right now!",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to escalation intent.",
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
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to booking intent.",
    },
    {
        "inputs": {
            "user_message": "Actually, how much does a dermatology consultation cost?",
            "conversation_history": [
                {"role": "user", "content": "I want to book an appointment."},
                {"role": "assistant", "content": "Sure! Are you already registered? Could you share your name and phone number?"},
            ],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to faq intent while keeping flow='booking'.",
    },
    {
        "inputs": {
            "user_message": "I need to cancel my appointment for tomorrow.",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to booking intent.",
    },
    {
        "inputs": {
            "user_message": "Actually, my phone number is wrong in your system — it should be 555-0199.",
            "conversation_history": [
                {"role": "user", "content": "Hi, I'm John Doe, phone +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! How can I help you today?"},
            ],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to escalation intent.",
    },
    {
        "inputs": {
            "user_message": "Hi, I'd like to book an appointment.",
            "conversation_history": [],
            "agent_under_test": "reception",
        },
        "expectations": "Proactively asks for contact information.",
    },
    {
        "inputs": {
            "user_message": "My phone number is +15550001234 and I am John Doe.",
            "conversation_history": [
                {"role": "user", "content": "Hi, I'd like to book an appointment with Dr. Sarah Collins."},
                {"role": "assistant", "content": "Hello! Are you already registered with us? Could you share your full name and phone number (or email) so I can look up your record?"},
            ],
            "agent_under_test": "reception",
        },
        "expectations": "Calls find_contact_tool.",
    },
    {
        "inputs": {
            "user_message": "My number is 555-9999, but I've never been there before.",
            "conversation_history": [
                {"role": "user", "content": "I need to book a session."},
                {"role": "assistant", "content": "Hello! Are you already registered? Could you share your name and phone number?"},
            ],
            "agent_under_test": "reception",
        },
        "expectations": "Calls find_contact_tool, then asks for new user details.",
    },
    {
        "inputs": {
            "user_message": "The appointment is for my daughter Emma.",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! I see you have two patients linked to your account: Lucas and Emma. Who is this appointment for?"},
            ],
            "agent_under_test": "reception",
        },
        "expectations": "Calls select_patient_tool with Emma's patient_id.",
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
            "agent_under_test": "reception",
        }, 
        "expectations": "Handles patient switching.",
    },
    {
        "inputs": {
            "user_message": "Actually, my phone number is wrong — it should be 555-0199.",
            "conversation_history": [
                {"role": "user", "content": "Hi, I'm John Doe, phone +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! How can I help you today?"},
            ],
            "agent_under_test": "reception",
        },
        "expectations": "Does NOT call update_contact_tool. Escalates.",
    },
    {
        "inputs": {
            "user_message": "Hi.",
            "conversation_history": [],
            "agent_under_test": "reception",
        },
        "expectations": "Reception proactively asks for contact identification.",
    },
    {
        "inputs": {
            "user_message": "Do you have anything next Tuesday with a cardiologist?",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! I've selected you as the patient. How can I help you today?"},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Calls check_availability_tool.",
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
        "expectations": "Asks for explicit confirmation BEFORE calling reserve_slot_tool.",
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
        "expectations": "Calls reserve_slot_tool.",
    },
    {
        "inputs": {
            "user_message": "I need to cancel my appointment for tomorrow.",
            "conversation_history": [
                {"role": "user", "content": "Hi, +15550001234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help?"},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Calls cancel_appointment_tool.",
    },
    {
        "inputs": {
            "user_message": "I need to reschedule my Thursday appointment to next week.",
            "conversation_history": [
                {"role": "user", "content": "Hi, +15550001234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help?"},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Uses reschedule_appointment_tool.",
    },
    {
        "inputs": {
            "user_message": "I need an endocrinologist.",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help you today?"},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Calls check_availability_tool.",
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
        "expectations": "Acknowledges payment. Does NOT call tools.",
    },
    {
        "inputs": {
            "user_message": "What happens if I'm late to my appointment?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expectations": "Calls search_faq_tool.",
    },
    {
        "inputs": {
            "user_message": "Do you accept Blue Cross insurance?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expectations": "Calls search_faq_tool.",
    },
    {
        "inputs": {
            "user_message": "What specialties do you offer?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expectations": "Calls search_faq_tool.",
    },
    {
        "inputs": {
            "user_message": "How much does a dermatology consultation cost?",
            "conversation_history": [
                {"role": "user", "content": "I want to book a cardiology appointment."},
                {"role": "assistant", "content": "Sure! Are you registered? Please share your name and phone number."},
            ],
            "agent_under_test": "faq",
        },
        "expectations": "Calls search_services_tool.",
    },
    {
        "inputs": {
            "user_message": "Can I book an appointment for tomorrow?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expectations": "Handles booking directly.",
    },
    {
        "inputs": {
            "user_message": "I have a headache, what medicine should I take?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expectations": "Does NOT provide medical advice.",
    },
]

# =========================================================================
# EXPANDED PHASE B RECORDS (23 NEW RECORDS)
# =========================================================================
NEW_RECORDS = [
    {
        "inputs": {
            "user_message": "Can I get my medical records sent to me?",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to escalation intent.",
    },
    {
        "inputs": {
            "user_message": "I want to change my primary care physician.",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to escalation intent.",
    },
    {
        "inputs": {
            "user_message": "Who is the best doctor for back pain?",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to faq intent.",
    },
    {
        "inputs": {
            "user_message": "Can I pay my bill online?",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to faq intent.",
    },
    {
        "inputs": {
            "user_message": "Where are you located?",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to faq intent.",
    },
    {
        "inputs": {
            "user_message": "I lost my prescription.",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to escalation intent.",
    },
    {
        "inputs": {
            "user_message": "Can I add a dependent to my account?",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to escalation intent.",
    },
    {
        "inputs": {
            "user_message": "Is telehealth available?",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to faq intent.",
    },
    {
        "inputs": {
            "user_message": "I want to complain about Dr. Smith.",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to escalation intent.",
    },
    {
        "inputs": {
            "user_message": "What is the parking situation?",
            "conversation_history": [],
            "agent_under_test": "coordinator",
        },
        "expectations": "Routes to faq intent.",
    },
    {
        "inputs": {
            "user_message": "I forgot my patient ID.",
            "conversation_history": [],
            "agent_under_test": "reception",
        },
        "expectations": "Proactively asks for other identifiers like full name and phone or email to do a lookup.",
    },
    {
        "inputs": {
            "user_message": "My name is Jane Smith, +14443332222.",
            "conversation_history": [
                {"role": "user", "content": "I need to book a session."},
                {"role": "assistant", "content": "Hello! Are you already registered? Could you share your name and phone number?"},
            ],
            "agent_under_test": "reception",
        },
        "expectations": "Calls find_contact_tool.",
    },
    {
        "inputs": {
            "user_message": "I don't have a phone number.",
            "conversation_history": [
                {"role": "user", "content": "I need to book a session."},
                {"role": "assistant", "content": "Hello! Are you already registered? Could you share your name and phone number?"},
            ],
            "agent_under_test": "reception",
        },
        "expectations": "Asks for email address or another form of identification to lookup the contact.",
    },
    {
        "inputs": {
            "user_message": "It's for my son, Michael.",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +14443332222."},
                {"role": "assistant", "content": "Welcome back, Jane! I see you have one patient linked to your account: Michael. Who is this appointment for?"},
            ],
            "agent_under_test": "reception",
        },
        "expectations": "Calls select_patient_tool with Michael's patient_id.",
    },
    {
        "inputs": {
            "user_message": "Wait, I need to update my email address.",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +14443332222."},
                {"role": "assistant", "content": "Welcome back, Jane!"},
            ],
            "agent_under_test": "reception",
        },
        "expectations": "Escalates to a human agent, as self-service data corrections are not allowed.",
    },
    {
        "inputs": {
            "user_message": "Do you have any availability for a general checkup this Friday?",
            "conversation_history": [
                {"role": "user", "content": "Hi, my phone is +15550001234."},
                {"role": "assistant", "content": "Welcome back, John! I've selected you as the patient. How can I help you today?"},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Calls check_availability_tool with specialty='general' or 'checkup' and start_date for this Friday.",
    },
    {
        "inputs": {
            "user_message": "I want the 9am slot with Dr. Adams.",
            "conversation_history": [
                {"role": "user", "content": "Do you have anything this Friday for a checkup?"},
                {"role": "assistant", "content": "Here are the available slots for Friday:\n- Dr. Adams at 09:00 AM\n- Dr. Adams at 14:00\n- Dr. Evans at 11:30 AM"},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Asks for explicit confirmation of the 9am slot with Dr. Adams.",
    },
    {
        "inputs": {
            "user_message": "Yes, that's correct.",
            "conversation_history": [
                {"role": "user", "content": "I want the 9am slot with Dr. Adams."},
                {"role": "assistant", "content": "To confirm — you'd like the 09:00 AM slot with Dr. Adams on Friday. Is that correct?"},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Calls reserve_slot_tool.",
    },
    {
        "inputs": {
            "user_message": "I want to cancel my reservation with Dr. Adams.",
            "conversation_history": [
                {"role": "user", "content": "Hi, +15550001234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help?"},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Calls cancel_appointment_tool (or cancel_reservation_tool).",
    },
    {
        "inputs": {
            "user_message": "Can I reschedule my appointment with Dr. Silva to tomorrow?",
            "conversation_history": [
                {"role": "user", "content": "Hi, +15550001234 (John Doe)."},
                {"role": "assistant", "content": "Welcome back John! How can I help?"},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Uses reschedule_appointment_tool.",
    },
    {
        "inputs": {
            "user_message": "[System Event: Payment Expired]",
            "conversation_history": [
                {"role": "user", "content": "Yes, please book the 10am slot."},
                {"role": "assistant", "content": "I've reserved the 10:00 AM slot with Dr. Silva. A payment link will be generated shortly. The slot is held temporarily."},
            ],
            "agent_under_test": "booking",
        },
        "expectations": "Acknowledges that the payment expired and the reservation was released. Asks if they want to try booking again.",
    },
    {
        "inputs": {
            "user_message": "Do you accept Medicare?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expectations": "Calls search_faq_tool.",
    },
    {
        "inputs": {
            "user_message": "What should I do if my arm hurts?",
            "conversation_history": [],
            "agent_under_test": "faq",
        },
        "expectations": "Does NOT provide medical advice. Recommends consulting a doctor.",
    },
]

PHASE_B_RECORDS = ORIGINAL_27_RECORDS + NEW_RECORDS


def generate_dataset(name: str, records: list, purge: bool = False) -> None:
    """
    Create or update an MLflow evaluation dataset.

    Records are passed directly to ``merge_records`` — no field transformation.
    Every record is stamped with ``{"dataset_version": DATASET_VERSION}`` in its
    ``tags`` so that consumers can filter or audit by version without changing
    the dataset name.

    Args:
        name:    Dataset name (stable across versions — version lives in tags).
        records: List of dicts with ``inputs`` and ``expectations`` keys, matching
                 the MLflow EvaluationDataset record schema.
        purge:   If ``True``, delete all existing records before inserting.
                 Use this to correct datasets that were seeded with wrong data.
                 Defaults to ``False`` to avoid accidental data loss.
    """
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
            print(f"Dataset '{name}' already exists — merging {len(records)} record(s)...")
    except Exception:
        print(f"Creating dataset '{name}'...")
        dataset = create_dataset(
            name=name,
            experiment_id=[experiment_id],
        )

    # MLflow's EvaluationDataset schema requires `expectations` to be a dict, not a str.
    # Source records store expectations as plain strings for readability; we normalise
    # them here into {"criteria": str} so the scorer template can reference
    # {{ expectations.criteria }}.
    # We also stamp each record with the current dataset_version tag.
    versioned = [
        {
            **r,
            "expectations": (
                {"criteria": r["expectations"]}
                if isinstance(r.get("expectations"), str)
                else r.get("expectations", {})
            ),
            "tags": {**r.get("tags", {}), "dataset_version": DATASET_VERSION},
        }
        for r in records
    ]
    dataset.merge_records(versioned)
    print(f"Dataset '{name}' now has {len(dataset.to_df())} record(s) (version={DATASET_VERSION}).")


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
    print("Creating Datasets")
    print(f"  version : {DATASET_VERSION}")
    print(f"  purge   : {args.purge}")
    print("=" * 60)
    generate_dataset("sanity-check-5q", SANITY_RECORDS, purge=args.purge)
    generate_dataset("prompt-eval-v1", PHASE_B_RECORDS, purge=args.purge)
    print("=" * 60)
