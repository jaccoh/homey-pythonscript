"""Tests for Run Named Script flow card helpers."""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_script_manager_importable_for_named_cards():
    """ScriptManager can be imported from app.py context."""
    from pythonscript.script_manager import ScriptManager

    sm = ScriptManager(Path("/tmp/test_sm_named"))
    assert hasattr(sm, "list_scripts")
    assert hasattr(sm, "get_script")


class TestAutocompleteScriptName:
    """Unit tests for _autocomplete_script_name helper logic (without Homey SDK)."""

    def _make_sm_results(self):
        return [
            {"name": "hello", "size": 100},
            {"name": "weather", "size": 250},
            {"name": "sunrise", "size": 180},
        ]

    def _autocomplete_logic(self, scripts, query):
        """Mirrors the logic in PythonScriptApp._autocomplete_script_name."""
        return [
            {"name": s["name"], "description": f"{s['size']} bytes"}
            for s in scripts
            if not query or query.lower() in s["name"].lower()
        ]

    def test_no_query_returns_all(self):
        scripts = self._make_sm_results()
        result = self._autocomplete_logic(scripts, "")
        assert len(result) == 3

    def test_query_filters_by_name(self):
        scripts = self._make_sm_results()
        result = self._autocomplete_logic(scripts, "sun")
        assert len(result) == 1
        assert result[0]["name"] == "sunrise"

    def test_description_includes_size(self):
        scripts = self._make_sm_results()
        result = self._autocomplete_logic(scripts, "hello")
        assert result[0]["description"] == "100 bytes"

    def test_query_case_insensitive(self):
        scripts = self._make_sm_results()
        result = self._autocomplete_logic(scripts, "WEATH")
        assert len(result) == 1
        assert result[0]["name"] == "weather"

    def test_no_match_returns_empty(self):
        scripts = self._make_sm_results()
        result = self._autocomplete_logic(scripts, "zzz")
        assert result == []


class TestExecuteNamedLogic:
    """Unit tests for _execute_named argument parsing logic."""

    def _parse_script_name(self, raw):
        """Mirrors the name-parsing logic in _execute_named."""
        if isinstance(raw, dict):
            raw = raw.get("name", "")
        return str(raw).strip()

    def test_string_name_passed_through(self):
        assert self._parse_script_name("hello") == "hello"

    def test_dict_name_extracted(self):
        assert self._parse_script_name({"name": "weather", "description": "250 bytes"}) == "weather"

    def test_empty_string_stays_empty(self):
        assert self._parse_script_name("") == ""

    def test_whitespace_stripped(self):
        assert self._parse_script_name("  sunrise  ") == "sunrise"

    def test_dict_missing_name_key_gives_empty(self):
        assert self._parse_script_name({"description": "no name"}) == ""

    def test_none_becomes_empty_string(self):
        # card_arguments.get("script_name") or "" → None becomes ""
        raw = None or ""
        assert self._parse_script_name(raw) == ""


@pytest.mark.asyncio
async def test_execute_named_missing_script_raises_value_error(tmp_path):
    """_execute_named wraps FileNotFoundError from ScriptManager as ValueError."""
    # app.py imports 'homey' (the Homey SDK), which is not installed in test
    # environments.  Inject a minimal stub so the module can be loaded.
    homey_app_stub = MagicMock()
    homey_app_stub.App = object  # PythonScriptApp will inherit from plain object
    homey_stub = MagicMock()
    homey_stub.app = homey_app_stub

    with patch.dict(sys.modules, {"homey": homey_stub, "homey.app": homey_app_stub}):
        sys.modules.pop("app", None)  # force fresh import under the stub
        import app as app_module

        try:
            app_instance = object.__new__(app_module.PythonScriptApp)
            app_instance._executor = MagicMock()

            # Script does not exist in tmp_path → ScriptManager raises FileNotFoundError
            # _execute_named must convert that to ValueError.
            with patch.object(app_module, "_SCRIPTS_ROOT", tmp_path):
                with pytest.raises(ValueError, match="not found"):
                    await app_instance._execute_named(
                        {"script_name": "nonexistent", "timeout": 30},
                        args=None,
                    )
        finally:
            sys.modules.pop("app", None)  # clean up so other tests are unaffected
