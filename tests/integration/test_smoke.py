"""Smoke tests: app running, basic script execution, error handling."""

import pytest

pytestmark = pytest.mark.integration


class TestAppRunning:
    def test_app_installed(self, shs):
        info = shs.app_info()
        assert info.get("id") == "nl.hoeve.pythonscript"

    def test_app_version_matches(self, shs):
        import json
        from pathlib import Path
        expected = json.loads(
            (Path(__file__).parent.parent.parent / "app.json").read_text()
        )["version"]
        info = shs.app_info()
        assert info.get("version") == expected


class TestScriptExecution:
    def test_return_integer(self, shs):
        r = shs.exec("return 42")
        assert r["return_value"] == "42"

    def test_return_string(self, shs):
        r = shs.exec('return "hello"')
        assert r["return_value"] == "hello"

    def test_return_none(self, shs):
        r = shs.exec("x = 1")
        assert r["return_value"] == ""

    def test_args_passed(self, shs):
        r = shs.exec("return args", args="myarg")
        assert r["return_value"] == "myarg"

    def test_set_tag(self, shs):
        r = shs.exec('homey.set_tag("score", 99)\nreturn None')
        assert r["tags"]["score"] == "99"

    def test_multiline_script(self, shs):
        script = "x = 2\ny = 3\nreturn x * y"
        r = shs.exec(script)
        assert r["return_value"] == "6"

    def test_async_sleep(self, shs):
        r = shs.exec("import asyncio\nawait asyncio.sleep(0.1)\nreturn 'ok'")
        assert r["return_value"] == "ok"

    def test_script_error_raises(self, shs):
        with pytest.raises(RuntimeError, match="boom"):
            shs.exec("raise ValueError('boom')")

    def test_timeout_enforced(self, shs):
        with pytest.raises(RuntimeError, match="timeout|exceeded"):
            shs.exec("import asyncio\nawait asyncio.sleep(10)", timeout=2)
