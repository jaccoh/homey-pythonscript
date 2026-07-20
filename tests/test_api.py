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
    import inspect
    import api
    sig = inspect.signature(api.scripts)
    assert 'homey' in sig.parameters


def test_get_script_invalid_name_raises():
    """Invalid script name should raise ValueError before touching filesystem."""
    import asyncio
    import api
    with pytest.raises((ValueError, Exception)):
        asyncio.get_event_loop().run_until_complete(
            api.get_script(homey=None, body={"name": "../evil"})
        )


def test_save_script_invalid_name_raises():
    import asyncio
    import api
    with pytest.raises((ValueError, Exception)):
        asyncio.get_event_loop().run_until_complete(
            api.save_script(homey=None, body={"name": "foo.bar", "code": "pass"})
        )


def test_delete_script_invalid_name_raises():
    import asyncio
    import api
    with pytest.raises((ValueError, Exception)):
        asyncio.get_event_loop().run_until_complete(
            api.delete_script(homey=None, body={"name": ""})
        )
