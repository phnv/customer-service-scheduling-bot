import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env file
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ Error: OPENAI_API_KEY is not set in the environment or .env file.")
    exit(1)

# Mask the API key for display
masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 10 else "invalid"
print(f"Found OPENAI_API_KEY: {masked_key}")

print("Testing connection to OpenAI API using SDK...")

try:
    client = OpenAI(api_key=api_key)
    
    response = client.responses.create(
        model="gpt-4o-mini",
        input="Hello, respond with 'OpenAI Key is working!' in one line."
    )
    
    print("✅ Success! Response from OpenAI:")
    print(f"   -> {response.output_text.strip()}")
except Exception as e:
    print(f"❌ Request failed with exception: {e}")

