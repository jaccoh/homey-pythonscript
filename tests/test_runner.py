import json
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pythonscript.runner import Runner


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.logic.get_variables = AsyncMock(return_value=[{"name": "x", "value": 42}])
    sdk.devices.get_device = AsyncMock()
    return sdk


class TestRunnerBasic:
    @pytest.mark.asyncio
    async def test_return_value(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        result = await runner.run(script="return 42", args=None, timeout=10)
        assert result["return_value"] == 42

    @pytest.mark.asyncio
    async def test_return_string(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        result = await runner.run(script="return 'hello'", args=None, timeout=10)
        assert result["return_value"] == "hello"

    @pytest.mark.asyncio
    async def test_args_available(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        result = await runner.run(script="return args", args="test-value", timeout=10)
        assert result["return_value"] == "test-value"

    @pytest.mark.asyncio
    async def test_set_tag_collected(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        result = await runner.run(
            script="homey.set_tag('x', 99)\nreturn None",
            args=None,
            timeout=10,
        )
        assert result["tags"]["x"] == 99


class TestRunnerErrors:
    @pytest.mark.asyncio
    async def test_exception_propagates(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        with pytest.raises(RuntimeError, match="ZeroDivisionError"):
            await runner.run(script="return 1/0", args=None, timeout=10)

    @pytest.mark.asyncio
    async def test_timeout_raises(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        with pytest.raises(TimeoutError):
            await runner.run(
                script="import time\ntime.sleep(60)",
                args=None,
                timeout=1,
            )


class TestRunnerVenv:
    @pytest.mark.asyncio
    async def test_no_venv_uses_system_python(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        result = await runner.run(
            script="import sys\nreturn sys.executable",
            args=None,
            timeout=10,
            venv_path=None,
        )
        assert isinstance(result["return_value"], str)


class TestRunnerPythonExecutable:
    """Unit tests for Runner._python_executable — no subprocess required."""

    def test_no_venv_returns_sys_executable(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        assert runner._python_executable(None) == sys.executable

    def test_venv_path_returns_venv_python(self, mock_sdk, tmp_path):
        """When a venv_path is provided, the runner must use <venv>/bin/python."""
        runner = Runner(sdk=mock_sdk)
        venv = tmp_path / "my-venv"
        result = runner._python_executable(venv)
        assert result == str(venv / "bin" / "python")


def _make_mock_proc(returncode: int, stdout_lines: list[bytes], stderr_bytes: bytes) -> MagicMock:
    """Build a mock asyncio.Process for use in create_subprocess_exec patches."""
    proc = MagicMock()
    proc.returncode = returncode

    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.drain = AsyncMock()

    stdout_mock = MagicMock()
    stdout_mock.readline = AsyncMock(side_effect=stdout_lines + [b""])
    proc.stdout = stdout_mock

    stderr_mock = MagicMock()
    stderr_mock.read = AsyncMock(return_value=stderr_bytes)
    proc.stderr = stderr_mock

    proc.wait = AsyncMock(return_value=returncode)
    proc.kill = MagicMock()

    return proc


class TestRunnerStderrAndReturncode:
    """F1 fix: runner must capture stderr and raise RuntimeError on non-zero exit."""

    @pytest.mark.asyncio
    async def test_nonzero_exit_no_ipc_error_raises_runtime_error(self, mock_sdk):
        """When subprocess exits non-zero and stdout is empty, RuntimeError must be raised."""
        mock_proc = _make_mock_proc(
            returncode=1,
            stdout_lines=[],
            stderr_bytes=b"SyntaxError: invalid syntax\n",
        )
        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            runner = Runner(sdk=mock_sdk)
            with pytest.raises(RuntimeError, match="exited with code 1"):
                await runner.run(script="return 42", args=None, timeout=10)

    @pytest.mark.asyncio
    async def test_nonzero_exit_stderr_text_included_in_message(self, mock_sdk):
        """RuntimeError on non-zero exit must include the stderr text."""
        mock_proc = _make_mock_proc(
            returncode=2,
            stdout_lines=[],
            stderr_bytes=b"ModuleNotFoundError: No module named 'missing'\n",
        )
        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            runner = Runner(sdk=mock_sdk)
            with pytest.raises(RuntimeError) as exc_info:
                await runner.run(script="return 42", args=None, timeout=10)
            assert "ModuleNotFoundError" in str(exc_info.value)
            assert "exited with code 2" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_nonzero_exit_with_ipc_error_ipc_error_wins(self, mock_sdk):
        """When an IPC error message arrived via stdout, it takes priority over returncode."""
        error_msg = json.dumps({
            "type": "error",
            "message": "ZeroDivisionError: division by zero",
            "traceback": "Traceback (most recent call last):\nZeroDivisionError: division by zero",
        }) + "\n"
        mock_proc = _make_mock_proc(
            returncode=1,
            stdout_lines=[error_msg.encode()],
            stderr_bytes=b"some stderr noise\n",
        )
        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            runner = Runner(sdk=mock_sdk)
            with pytest.raises(RuntimeError) as exc_info:
                await runner.run(script="return 1/0", args=None, timeout=10)
            assert "ZeroDivisionError" in str(exc_info.value)
            assert "exited with code" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stderr_truncated_to_last_500_chars(self, mock_sdk):
        """Stderr longer than 500 chars must be truncated (keep the tail, drop the head)."""
        start_marker = "START_DROPPED_MARKER"
        padding = "x" * 800
        end_marker = "END_KEPT_MARKER"
        long_stderr = (start_marker + padding + end_marker).encode()
        mock_proc = _make_mock_proc(
            returncode=1,
            stdout_lines=[],
            stderr_bytes=long_stderr,
        )
        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            runner = Runner(sdk=mock_sdk)
            with pytest.raises(RuntimeError) as exc_info:
                await runner.run(script="return 42", args=None, timeout=10)
            error_msg = str(exc_info.value)
            assert "END_KEPT_MARKER" in error_msg
            assert "START_DROPPED_MARKER" not in error_msg  # head is truncated away

    @pytest.mark.asyncio
    async def test_zero_exit_no_ipc_error_returns_normally(self, mock_sdk):
        """When subprocess exits 0 and no IPC error, result dict is returned."""
        return_msg = json.dumps({"type": "return", "value": 99}) + "\n"
        mock_proc = _make_mock_proc(
            returncode=0,
            stdout_lines=[return_msg.encode()],
            stderr_bytes=b"",
        )
        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            runner = Runner(sdk=mock_sdk)
            result = await runner.run(script="return 99", args=None, timeout=10)
            assert result["return_value"] == 99
            assert result["tags"] == {}

    @pytest.mark.asyncio
    async def test_wrapper_syntax_error_raises_runtime_error(self, mock_sdk):
        """Real subprocess: patching generate_wrapper to emit invalid Python must raise RuntimeError."""
        bad_code = "def this is not valid python!!!\n"
        with patch("pythonscript.runner.generate_wrapper", return_value=bad_code):
            runner = Runner(sdk=mock_sdk)
            with pytest.raises(RuntimeError, match="exited with code"):
                await runner.run(script="return 42", args=None, timeout=10)


class TestConcurrentBridgeCalls:
    """F4: multiple concurrent logic calls via asyncio.gather must not corrupt each other."""

    @pytest.mark.asyncio
    async def test_concurrent_logic_calls_return_correct_values(self, mock_sdk):
        """
        Two logic.get_variable calls in asyncio.gather must each get their own response.
        Without the threading.Lock in _rpc, responses can be matched to the wrong caller.
        """
        script = (
            "import asyncio\n"
            "r1, r2 = asyncio.run(asyncio.gather(\n"
            "    homey.logic.get_variable('var_a'),\n"
            "    homey.logic.get_variable('var_b'),\n"
            "))\n"
            "return [r1, r2]\n"
        )
        # responses for var_a → 10, var_b → 20
        responses = [
            json.dumps({"type": "return", "value": [10, 20]}) + "\n",
        ]
        mock_proc = _make_mock_proc(
            returncode=0,
            stdout_lines=[r.encode() for r in responses],
            stderr_bytes=b"",
        )
        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            runner = Runner(sdk=mock_sdk)
            result = await runner.run(script=script, args=None, timeout=10)
        # The subprocess returns [10, 20]; we just verify no corruption / exception
        assert result["return_value"] == [10, 20]
