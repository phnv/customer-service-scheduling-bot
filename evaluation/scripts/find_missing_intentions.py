import json
from scripts.create_datasets import SANITY_RECORDS, FULL_RECORDS

missing = []

for idx, record in enumerate(SANITY_RECORDS):
    if "expected_intention" not in record.get("expectations", {}):
        missing.append(("SANITY_RECORDS", idx, record["inputs"]["user_message"]))

for idx, record in enumerate(FULL_RECORDS):
    if "expected_intention" not in record.get("expectations", {}):
        missing.append(("FULL_RECORDS", idx, record["inputs"]["user_message"]))

if not missing:
    print("No records missing expected_intention.")
else:
    for m in missing:
        print(f"Dataset: {m[0]}, Index: {m[1]}")
        print(f"User Message: {m[2]}")
        print("---")
