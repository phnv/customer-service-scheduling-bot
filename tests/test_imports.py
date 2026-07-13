import sys
import pathlib
import importlib
import traceback
import os

project_root = "/home/phen/projects/customer-service-scheduling-bot"
sys.path.insert(0, project_root)

has_error = False

for d in ['app', 'ui']:
    for p in pathlib.Path(project_root).joinpath(d).rglob("*.py"):
        # Relativize to project root
        rel_p = p.relative_to(project_root)
        mod_name = str(rel_p.with_suffix("")).replace(os.sep, ".")
        try:
            importlib.import_module(mod_name)
        except ImportError as e:
            print(f"[{mod_name}] ImportError: {e}")
            has_error = True
        except Exception as e:
            print(f"[{mod_name}] Exception during import: {e}")
            has_error = True

if has_error:
    sys.exit(1)
else:
    print("All imports successful.")
