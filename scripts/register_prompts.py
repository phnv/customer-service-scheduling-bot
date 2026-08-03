"""
Register all agent prompts to the MLflow Prompt Registry.

Each agent's system prompt string is registered as a separate, versioned
entry in the registry. This enables:
  - Version history and diff tracking for every prompt change
  - Alias-based loading (e.g., @champion, @production) without code changes
  - Linkage to registered models via prompt URIs

Prompts registered:
  - coordinator-prompt   (app/prompts/coordinator.py → COORDINATOR_PROMPT)
  - reception-prompt     (app/prompts/reception.py   → RECEPTION_PROMPT)
  - booking-prompt       (app/prompts/booking.py     → BOOKING_PROMPT)
  - faq-prompt           (app/prompts/faq.py         → FAQ_PROMPT)
  - escalation-prompt    (app/prompts/escalation.py  → ESCALATION_PROMPT)

Note: At runtime the app still imports prompts directly from Python modules.
      mlflow.genai.load_prompt() is used when loading from a registry alias.

Usage:
    uv run python scripts/register_prompts.py

Output:
    Saves latest prompt URIs to scripts/.latest_prompt_uris.json for use
    by register_model.py.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import mlflow

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db")
experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "customer-service-scheduling-bot")

mlflow.set_tracking_uri(tracking_uri)
mlflow.set_experiment(experiment_name)

# Add project root to path so app.prompts can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.prompts.coordinator import COORDINATOR_PROMPT
from app.prompts.reception import RECEPTION_PROMPT
from app.prompts.booking import BOOKING_PROMPT
from app.prompts.faq import FAQ_PROMPT
from app.prompts.escalation import ESCALATION_PROMPT

# ---------------------------------------------------------------------------
# Prompts to register
# Each entry: (registry_name, prompt_template_string)
# ---------------------------------------------------------------------------
PROMPTS: list[tuple[str, str]] = [
    ("coordinator-prompt", COORDINATOR_PROMPT),
    ("reception-prompt", RECEPTION_PROMPT),
    ("booking-prompt", BOOKING_PROMPT),
    ("faq-prompt", FAQ_PROMPT),
    ("escalation-prompt", ESCALATION_PROMPT),
]

# Path where latest prompt URIs are persisted for register_model.py
URIS_OUTPUT_PATH = Path(__file__).parent / ".latest_prompt_uris.json"


def main() -> None:
    print("=" * 60)
    print("Registering Agent Prompts to MLflow Prompt Registry")
    print(f"  experiment : {experiment_name}")
    print(f"  tracking   : {tracking_uri}")
    print("=" * 60)

    latest_uris: dict[str, str] = {}

    for name, template in PROMPTS:
        registered = mlflow.genai.register_prompt(
            name=name,
            template=template,
        )
        uri = f"prompts:/{registered.name}/{registered.version}"
        latest_uris[name] = uri
        print(f"  ✓ {name:30s}  v{registered.version}  →  {uri}")

    # Persist URIs so register_model.py can link the model to these prompts.
    URIS_OUTPUT_PATH.write_text(json.dumps(latest_uris, indent=2))
    print()
    print(f"  Prompt URIs saved to: {URIS_OUTPUT_PATH}")
    print("=" * 60)
    print("Done. Set aliases with:")
    print("  uv run python scripts/manage_aliases.py prompt coordinator-prompt 1 champion")
    print("=" * 60)


if __name__ == "__main__":
    main()
