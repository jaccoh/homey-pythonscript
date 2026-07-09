"""
End-to-end tests for the sandboxed Runner path.

These tests spawn real subprocesses via Runner(sandboxed=True).
The subprocess uses sys.executable (local venv), so RestrictedPython must be installed.
"""
import time
import pytest
from unittest.mock import MagicMock
from pythonscript.runner import Runner


@pytest.fixture
def sdk():
    return MagicMock()


async def _run(sdk, script, args=None, timeout=10):
    runner = Runner(sdk=sdk)
    return await runner.run(
        script=script,
        args=args,
        timeout=timeout,
        venv_path=None,
        sandboxed=True,
    )


class TestSandboxSubprocessBasics:
    @pytest.mark.asyncio
    async def test_return_integer(self, sdk):
        r = await _run(sdk, "return 42")
        assert r["return_value"] == 42

    @pytest.mark.asyncio
    async def test_return_string(self, sdk):
        r = await _run(sdk, "return 'hello'")
        assert r["return_value"] == "hello"

    @pytest.mark.asyncio
    async def test_return_none(self, sdk):
        r = await _run(sdk, "x = 1")
        assert r["return_value"] is None

    @pytest.mark.asyncio
    async def test_args_injected(self, sdk):
        r = await _run(sdk, "return args", args="myarg")
        assert r["return_value"] == "myarg"

    @pytest.mark.asyncio
    async def test_arithmetic(self, sdk):
        r = await _run(sdk, "x = 2 * 21\nreturn x")
        assert r["return_value"] == 42

    @pytest.mark.asyncio
    async def test_allowed_import_math(self, sdk):
        r = await _run(sdk, "import math\nreturn math.sqrt(16)")
        assert r["return_value"] == 4.0

    @pytest.mark.asyncio
    async def test_allowed_import_json(self, sdk):
        r = await _run(sdk, "import json\nreturn json.dumps({'k': 1})")
        assert r["return_value"] == '{"k": 1}'

    @pytest.mark.asyncio
    async def test_set_tag_via_ipc(self, sdk):
        r = await _run(sdk, "homey.set_tag('score', 99)\nreturn None")
        assert r["tags"]["score"] == 99

    @pytest.mark.asyncio
    async def test_multiple_tags(self, sdk):
        r = await _run(sdk, "homey.set_tag('a', 1)\nhomey.set_tag('b', 'x')\nreturn None")
        assert r["tags"]["a"] == 1
        assert r["tags"]["b"] == "x"


class TestSandboxSubprocessRestrictions:
    @pytest.mark.asyncio
    async def test_import_os_blocked(self, sdk):
        with pytest.raises(RuntimeError, match="not allowed"):
            await _run(sdk, "import os")

    @pytest.mark.asyncio
    async def test_import_subprocess_blocked(self, sdk):
        with pytest.raises(RuntimeError, match="not allowed"):
            await _run(sdk, "import subprocess")

    @pytest.mark.asyncio
    async def test_import_sys_blocked(self, sdk):
        with pytest.raises(RuntimeError, match="not allowed"):
            await _run(sdk, "import sys")

    @pytest.mark.asyncio
    async def test_import_requests_blocked(self, sdk):
        with pytest.raises(RuntimeError, match="not allowed"):
            await _run(sdk, "import requests")

    @pytest.mark.asyncio
    async def test_open_blocked(self, sdk):
        with pytest.raises(RuntimeError, match="not allowed"):
            await _run(sdk, "open('/etc/passwd')")

    @pytest.mark.asyncio
    async def test_exec_blocked(self, sdk):
        with pytest.raises(RuntimeError, match="not allowed"):
            await _run(sdk, "exec('import os')")

    @pytest.mark.asyncio
    async def test_dunder_attribute_blocked(self, sdk):
        with pytest.raises(RuntimeError):
            await _run(sdk, "x = []\nx.__class__")

    @pytest.mark.asyncio
    async def test_no_await_in_sandbox(self, sdk):
        """Sandbox scripts are synchronous — await is a SyntaxError."""
        with pytest.raises((RuntimeError, SyntaxError)):
            await _run(sdk, "import asyncio\nawait asyncio.sleep(0)")


class TestSandboxSubprocessErrors:
    @pytest.mark.asyncio
    async def test_runtime_error_propagates(self, sdk):
        with pytest.raises(RuntimeError, match="boom"):
            await _run(sdk, "raise ValueError('boom')")

    @pytest.mark.asyncio
    async def test_syntax_error_propagates(self, sdk):
        with pytest.raises(RuntimeError):
            await _run(sdk, "def (")

    @pytest.mark.asyncio
    async def test_name_error_propagates(self, sdk):
        with pytest.raises(RuntimeError, match="undefined_var"):
            await _run(sdk, "return undefined_var")


class TestSandboxTimeoutKillsProcess:
    @pytest.mark.asyncio
    async def test_infinite_loop_killed_within_timeout(self, sdk):
        """Core fix: subprocess must be killed, not just timed out."""
        start = time.monotonic()
        with pytest.raises(TimeoutError):
            await _run(sdk, "while True:\n    pass", timeout=0.3)
        elapsed = time.monotonic() - start
        # Must complete within ~1s of the timeout (not hang indefinitely)
        assert elapsed < 2.0, f"Process not killed: took {elapsed:.1f}s"

    @pytest.mark.asyncio
    async def test_cpu_spin_killed_within_timeout(self, sdk):
        start = time.monotonic()
        with pytest.raises(TimeoutError):
            await _run(sdk, "x = 0\nwhile True:\n    x = x + 1", timeout=0.3)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0

    @pytest.mark.asyncio
    async def test_timeout_message_mentions_timeout(self, sdk):
        with pytest.raises(TimeoutError, match="timeout|exceeded"):
            await _run(sdk, "while True:\n    pass", timeout=0.2)

    @pytest.mark.asyncio
    async def test_normal_script_completes_before_timeout(self, sdk):
        r = await _run(sdk, "return 1", timeout=5)
        assert r["return_value"] == 1
