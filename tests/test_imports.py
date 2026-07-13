import pathlib
import importlib
import pytest
import os

project_root = "/home/phen/projects/customer-service-scheduling-bot"

def get_modules():
    modules = []
    for d in ['app', 'ui']:
        for p in pathlib.Path(project_root).joinpath(d).rglob("*.py"):
            rel_p = p.relative_to(project_root)
            mod_name = str(rel_p.with_suffix("")).replace(os.sep, ".")
            modules.append(mod_name)
    return modules

@pytest.mark.parametrize("mod_name", get_modules())
def test_import_module(mod_name):
    try:
        importlib.import_module(mod_name)
    except Exception as e:
        pytest.fail(f"Failed to import {mod_name}: {e}")
