"""
Manage MLflow aliases for registered models and prompts.

Aliases enable zero-downtime pointer updates:
  - @champion  → the best-performing version currently in use
  - @production → the live version serving real traffic
  - @staging   → the version under active testing

Updating an alias redirects all callers without any code changes.

Usage:
    # Set alias on a registered model
    uv run python scripts/manage_aliases.py model customer-service-scheduling-bot 1 champion

    # Set alias on a registered prompt
    uv run python scripts/manage_aliases.py prompt coordinator-prompt 1 champion

After setting:
    # Load by alias (in application code)
    prompt = mlflow.genai.load_prompt("prompts:/coordinator-prompt@champion")
    model  = mlflow.pyfunc.load_model("models:/customer-service-scheduling-bot@champion")
"""

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

import mlflow
from mlflow import MlflowClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///evaluation/mlflow.db")
experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "customer-service-scheduling-bot")

mlflow.set_tracking_uri(tracking_uri)
mlflow.set_experiment(experiment_name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage MLflow model and prompt aliases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python scripts/manage_aliases.py model customer-service-scheduling-bot 1 champion\n"
            "  uv run python scripts/manage_aliases.py prompt coordinator-prompt 1 champion\n"
            "  uv run python scripts/manage_aliases.py prompt booking-prompt 2 production\n"
        ),
    )
    parser.add_argument(
        "type",
        choices=["model", "prompt"],
        help="The type of artifact to alias.",
    )
    parser.add_argument(
        "name",
        type=str,
        help="The registered name of the artifact.",
    )
    parser.add_argument(
        "version",
        type=str,
        help="The version number to alias.",
    )
    parser.add_argument(
        "alias",
        type=str,
        help="The alias to assign (e.g., champion, production, staging).",
    )

    args = parser.parse_args()
    client = MlflowClient()

    if args.type == "model":
        print(f"Setting alias '{args.alias}' → model '{args.name}' v{args.version} ...")
        client.set_registered_model_alias(
            name=args.name,
            alias=args.alias,
            version=args.version,
        )
        print(f"  ✓ Done. Load via: models:/{args.name}@{args.alias}")

    elif args.type == "prompt":
        print(f"Setting alias '{args.alias}' → prompt '{args.name}' v{args.version} ...")
        try:
            version_int = int(args.version)
        except ValueError:
            print(f"ERROR: Prompt version must be an integer, got '{args.version}'.")
            sys.exit(1)
        mlflow.genai.set_prompt_alias(
            name=args.name,
            version=version_int,
            alias=args.alias,
        )
        print(f"  ✓ Done. Load via: prompts:/{args.name}@{args.alias}")


if __name__ == "__main__":
    main()
