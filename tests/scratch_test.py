from app.agents.graph import run_agent

print("--- Starting Agent Test ---")
response, state = run_agent("I want to book an appointment. My name is John Doe, phone +15550001234.")
print("\n--- Response ---")
print(response)
print("\n--- State ---")
print("Contact ID:", state.get("contact_id"))
print("Patient ID:", state.get("patient_id"))
print("Intent:", state.get("intent"))
print("Flow:", state.get("flow"))
