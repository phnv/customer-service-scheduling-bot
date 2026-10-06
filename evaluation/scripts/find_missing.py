import json
from scripts.create_datasets import SANITY_RECORDS, FULL_RECORDS

missing_facts = []

for idx, record in enumerate(SANITY_RECORDS):
    if "expected_facts" not in record.get("expectations", {}):
        missing_facts.append(("SANITY_RECORDS", idx, record["inputs"]["user_message"], record.get("expectations", {})))

for idx, record in enumerate(FULL_RECORDS):
    if "expected_facts" not in record.get("expectations", {}):
        missing_facts.append(("FULL_RECORDS", idx, record["inputs"]["user_message"], record.get("expectations", {})))

for mf in missing_facts:
    print(f"Dataset: {mf[0]}, Index: {mf[1]}")
    print(f"User Message: {mf[2]}")
    print(f"Current Expectations: {mf[3]}")
    print("---")
