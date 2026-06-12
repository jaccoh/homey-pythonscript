import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pythonscript.executor import Executor, ExecutionResult


@pytest.fixture
def mock_sdk():
    return MagicMock()


class TestExecutorRouting:
    @pytest.mark.asyncio
    async def test_sandboxed_flag_uses_sandbox(self, mock_sdk, tmp_path):
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Sandbox") as MockSandbox:
            instance = MockSandbox.return_value
            instance.run = AsyncMock(return_value={"return_value": 1, "tags": {}})
            result = await ex.run(
                script="return 1",
                args=None,
                sandbox=True,
                requirements="",
                timeout=30,
                card_uid="card-1",
            )
        MockSandbox.assert_called_once()
        assert result.return_value == 1

    @pytest.mark.asyncio
    async def test_no_sandbox_uses_runner(self, mock_sdk, tmp_path):
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner") as MockRunner:
            instance = MockRunner.return_value
            instance.run = AsyncMock(return_value={"return_value": 42, "tags": {"x": 1}})
            result = await ex.run(
                script="return 42",
                args=None,
                sandbox=False,
                requirements="",
                timeout=30,
                card_uid="card-1",
            )
        MockRunner.assert_called_once()
        assert result.return_value == 42
        assert result.tags["x"] == 1

    @pytest.mark.asyncio
    async def test_requirements_forces_runner(self, mock_sdk, tmp_path):
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner") as MockRunner:
            instance = MockRunner.return_value
            instance.run = AsyncMock(return_value={"return_value": None, "tags": {}})
            await ex.run(
                script="return 1",
                args=None,
                sandbox=True,
                requirements="requests==2.31.0",
                timeout=30,
                card_uid="card-1",
            )
        MockRunner.assert_called_once()

    @pytest.mark.asyncio
    async def test_return_value_stringified_for_homey(self, mock_sdk, tmp_path):
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Sandbox") as MockSandbox:
            instance = MockSandbox.return_value
            instance.run = AsyncMock(return_value={"return_value": 3.14, "tags": {}})
            result = await ex.run(
                script="return 3.14",
                args=None,
                sandbox=True,
                requirements="",
                timeout=30,
                card_uid="card-1",
            )
        assert result.homey_tokens["return_value"] == "3.14"
