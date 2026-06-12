import pytest
from unittest.mock import AsyncMock, MagicMock
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
