import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pythonscript.executor import Executor, ExecutionResult


@pytest.fixture
def mock_sdk():
    return MagicMock()


def _mock_runner(return_value=42, tags=None):
    """Patch Runner and return (MockRunner class, instance mock)."""
    mock_cls = MagicMock()
    instance = mock_cls.return_value
    instance.run = AsyncMock(return_value={"return_value": return_value, "tags": tags or {}})
    return mock_cls, instance


class TestExecutorRouting:
    @pytest.mark.asyncio
    async def test_sandbox_card_uses_runner_sandboxed(self, mock_sdk, tmp_path):
        """sandbox=True -> Runner.run(..., sandboxed=True), venv_path=None."""
        mock_cls, instance = _mock_runner(return_value=1)
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner", mock_cls):
            result = await ex.run(
                script="return 1",
                args=None,
                sandbox=True,
                requirements="",
                timeout=30,
                card_uid="sandboxed",
            )
        mock_cls.assert_called_once()
        kw = instance.run.call_args.kwargs
        assert kw["sandboxed"] is True
        assert kw["venv_path"] is None
        assert result.return_value == 1

    @pytest.mark.asyncio
    async def test_no_venv_sandbox_false_uses_runner_without_venv(self, mock_sdk, tmp_path):
        """sandbox=False, requirements="", card_uid="" -> Runner, venv_path=None, sandboxed=False."""
        mock_cls, instance = _mock_runner(return_value=42, tags={"x": 1})
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner", mock_cls):
            result = await ex.run(
                script="return 42",
                args=None,
                sandbox=False,
                requirements="",
                timeout=30,
                card_uid="",
            )
        kw = instance.run.call_args.kwargs
        assert kw["venv_path"] is None
        assert kw["sandboxed"] is False
        assert result.return_value == 42

    @pytest.mark.asyncio
    async def test_prebuilt_venv_sandbox_false_uses_venv_path(self, mock_sdk, tmp_path):
        """sandbox=False, card_uid non-empty -> Runner uses pre-built venv."""
        mock_cls, instance = _mock_runner()
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner", mock_cls):
            await ex.run(
                script="return 42",
                args=None,
                sandbox=False,
                requirements="",
                timeout=30,
                card_uid="my-env",
            )
        kw = instance.run.call_args.kwargs
        assert kw["venv_path"] == tmp_path / "my-env"
        assert kw["sandboxed"] is False

    @pytest.mark.asyncio
    async def test_packages_card_with_requirements_runner_gets_venv_path(self, mock_sdk, tmp_path):
        """sandbox=False + non-empty requirements -> Runner receives a non-None venv_path."""
        mock_cls, instance = _mock_runner(return_value=None)
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner", mock_cls):
            await ex.run(
                script="return 1",
                args=None,
                sandbox=False,
                requirements="requests==2.31.0",
                timeout=30,
                card_uid="my-venv",
            )
        kw = instance.run.call_args.kwargs
        assert kw["venv_path"] is not None
        assert "my-venv" in str(kw["venv_path"])

    @pytest.mark.asyncio
    async def test_return_value_stringified_for_homey(self, mock_sdk, tmp_path):
        mock_cls, _ = _mock_runner(return_value=3.14)
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner", mock_cls):
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
        """Sandbox card: optional argument defaults to None; Runner.run receives args=None."""
        mock_cls, instance = _mock_runner(return_value=None)
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner", mock_cls):
            await ex.run(
                script="return args",
                args=None,
                sandbox=True,
                requirements="",
                timeout=30,
                card_uid="sandboxed",
            )
        kw = instance.run.call_args.kwargs
        assert kw.get("args") is None

    @pytest.mark.asyncio
    async def test_sandbox_timeout_passed_to_runner(self, mock_sdk, tmp_path):
        """Executor passes the timeout value through to Runner.run()."""
        mock_cls, instance = _mock_runner(return_value=None)
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner", mock_cls):
            await ex.run(
                script="return None",
                args=None,
                sandbox=True,
                requirements="",
                timeout=7,
                card_uid="sandboxed",
            )
        kw = instance.run.call_args.kwargs
        assert kw["timeout"] == 7


class TestHomeyTokens:
    def test_homey_tokens_always_has_return_value_key(self):
        result = ExecutionResult(return_value="hello")
        assert "return_value" in result.homey_tokens

    def test_homey_tokens_always_has_error_key(self):
        result = ExecutionResult(return_value=None)
        assert "error" in result.homey_tokens

    def test_homey_tokens_return_value_empty_string_when_none(self):
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
