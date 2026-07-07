import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_api_exports_script_functions():
    import api
    assert callable(api.scripts)
    assert callable(api.get_script)
    assert callable(api.save_script)
    assert callable(api.delete_script)
    assert callable(api.run_script_api)


def test_api_scripts_function_signature():
    import inspect, api
    sig = inspect.signature(api.scripts)
    assert 'homey' in sig.parameters
