import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pythonscript.executor import Executor, ExecutionResult


@pytest.fixture
def mock_sdk():
    return MagicMock()


class TestExecutorRouting:
    """Tests for the Executor's routing logic between Sandbox and Runner."""

    @pytest.mark.asyncio
    async def test_sandbox_card_uses_sandbox(self, mock_sdk, tmp_path):
        """sandbox=True, requirements="" (the 'run_script' card) -> always uses Sandbox."""
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
                card_uid="sandboxed",
            )
        MockSandbox.assert_called_once()
        assert result.return_value == 1

    @pytest.mark.asyncio
    async def test_packages_card_no_requirements_uses_runner_without_venv(self, mock_sdk, tmp_path):
        """sandbox=False, requirements="" (packages card, no packages) -> Runner, venv_path=None."""
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
                card_uid="default",
            )
        MockRunner.assert_called_once()
        # venv_path must be None when there are no requirements
        call_kwargs = instance.run.call_args.kwargs
        assert call_kwargs.get("venv_path") is None
        assert result.return_value == 42
        assert result.tags["x"] == 1

    @pytest.mark.asyncio
    async def test_packages_card_with_requirements_runner_gets_venv_path(self, mock_sdk, tmp_path):
        """sandbox=False + non-empty requirements -> Runner receives a non-None venv_path."""
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner") as MockRunner:
            instance = MockRunner.return_value
            instance.run = AsyncMock(return_value={"return_value": None, "tags": {}})
            await ex.run(
                script="return 1",
                args=None,
                sandbox=False,
                requirements="requests==2.31.0",
                timeout=30,
                card_uid="my-venv",
            )
        MockRunner.assert_called_once()
        call_kwargs = instance.run.call_args.kwargs
        venv_path = call_kwargs.get("venv_path")
        assert venv_path is not None
        assert "my-venv" in str(venv_path)

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
                card_uid="sandboxed",
            )
        assert result.homey_tokens["return_value"] == "3.14"

    @pytest.mark.asyncio
    async def test_sandbox_card_args_none_when_not_provided(self, mock_sdk, tmp_path):
        """Sandbox card: optional argument defaults to None; Sandbox.run receives args=None."""
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Sandbox") as MockSandbox:
            instance = MockSandbox.return_value
            instance.run = AsyncMock(return_value={"return_value": None, "tags": {}})
            await ex.run(
                script="return args",
                args=None,
                sandbox=True,
                requirements="",
                timeout=30,
                card_uid="sandboxed",
            )
        call_kwargs = instance.run.call_args.kwargs
        assert call_kwargs.get("args") is None

    @pytest.mark.asyncio
    async def test_sandbox_timeout_raises_timeout_error(self, mock_sdk, tmp_path):
        """When sandbox execution exceeds the timeout, a TimeoutError is raised."""
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Sandbox") as MockSandbox:
            instance = MockSandbox.return_value

            async def _hang(*args, **kwargs):
                await asyncio.sleep(10)
                return {"return_value": None, "tags": {}}

            instance.run = _hang

            with pytest.raises(TimeoutError):
                await ex.run(
                    script="import time\ntime.sleep(999)",
                    args=None,
                    sandbox=True,
                    requirements="",
                    timeout=0.05,
                    card_uid="sandboxed",
                )


class TestHomeyTokens:
    """Tests for ExecutionResult.homey_tokens dict that Homey receives."""

    def test_homey_tokens_always_has_return_value_key(self):
        result = ExecutionResult(return_value="hello")
        assert "return_value" in result.homey_tokens

    def test_homey_tokens_always_has_error_key(self):
        result = ExecutionResult(return_value=None)
        assert "error" in result.homey_tokens

    def test_homey_tokens_return_value_empty_string_when_none(self):
        """None return_value is represented as empty string (not the string 'None')."""
        result = ExecutionResult(return_value=None)
        assert result.homey_tokens["return_value"] == ""

    def test_homey_tokens_return_value_stringified(self):
        result = ExecutionResult(return_value=42)
        assert result.homey_tokens["return_value"] == "42"

    def test_homey_tokens_float_stringified(self):
        result = ExecutionResult(return_value=3.14)
        assert result.homey_tokens["return_value"] == "3.14"

    def test_homey_tokens_tags_included_as_strings(self):
        result = ExecutionResult(return_value=None, tags={"temp": 21.5, "mode": "heat"})
        assert result.homey_tokens["temp"] == "21.5"
        assert result.homey_tokens["mode"] == "heat"

    def test_homey_tokens_error_key_empty_on_success(self):
        result = ExecutionResult(return_value="ok")
        assert result.homey_tokens["error"] == ""
