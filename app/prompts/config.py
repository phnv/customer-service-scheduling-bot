from datetime import datetime

def get_prompt_variables() -> dict:
    """Returns a dictionary of variables to be interpolated into prompts."""
    return {
        "ORGANIZATION_NAME": "ClinicOps",
        "BOOKING_TEAM_NAME": "Scheduling Team",
        "TODAY": datetime.now().strftime("%Y-%m-%d")
    }
