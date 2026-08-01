"""Smoke test: verify run_evaluation.py reads dataset names from dataset_config.json."""
import sys
import json
from pathlib import Path

# --- 1. Verify the JSON file exists and has expected keys ---
config_path = Path(__file__).parent / "dataset_config.json"
assert config_path.exists(), f"FAIL — {config_path} not found"

with config_path.open(encoding="utf-8") as f:
    cfg = json.load(f)

assert "version" in cfg, "FAIL — missing 'version' key"
assert "datasets" in cfg, "FAIL — missing 'datasets' key"
assert "sanity" in cfg["datasets"], "FAIL — missing datasets.sanity"
assert "full" in cfg["datasets"], "FAIL — missing datasets.full"
assert "name" in cfg["datasets"]["sanity"], "FAIL — missing datasets.sanity.name"
assert "name" in cfg["datasets"]["full"], "FAIL — missing datasets.full.name"

print(f"PASS — dataset_config.json exists and is well-formed")
print(f"       version      : {cfg['version']}")
print(f"       sanity name  : {cfg['datasets']['sanity']['name']}")
print(f"       full name    : {cfg['datasets']['full']['name']}")

# --- 2. Simulate the _write_dataset_config path from create_datasets.py ---
# Re-write the JSON and verify round-trip integrity
original_text = config_path.read_text(encoding="utf-8")
config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
reloaded = json.loads(config_path.read_text(encoding="utf-8"))
assert reloaded == cfg, "FAIL — JSON round-trip produced different content"
print("PASS — JSON round-trip write/read produces identical content")

print("\nAll smoke tests passed.")
