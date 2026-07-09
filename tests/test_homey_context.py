import pytest
from unittest.mock import AsyncMock, MagicMock
from pythonscript.homey_context import HomeyContext


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.settings.get = MagicMock(return_value=None)
    sdk.settings.set = MagicMock()
    return sdk


class TestSetTag:
    def test_set_tag_stores_value(self, mock_sdk):
        ctx = HomeyContext(sdk=mock_sdk)
        ctx.set_tag("temp", 22.5)
        assert ctx._tags["temp"] == 22.5

    def test_set_tag_multiple(self, mock_sdk):
        ctx = HomeyContext(sdk=mock_sdk)
        ctx.set_tag("a", 1)
        ctx.set_tag("b", "hello")
        assert ctx._tags == {"a": 1, "b": "hello"}


class TestLogic:
    @pytest.mark.asyncio
    async def test_get_variable(self, mock_sdk):
        mock_sdk.logic.get_variables = AsyncMock(
            return_value=[{"name": "temperature", "value": 21.5}]
        )
        ctx = HomeyContext(sdk=mock_sdk)
        result = await ctx.logic.get_variable("temperature")
        assert result == 21.5

    @pytest.mark.asyncio
    async def test_get_variable_not_found_returns_none(self, mock_sdk):
        mock_sdk.logic.get_variables = AsyncMock(return_value=[])
        ctx = HomeyContext(sdk=mock_sdk)
        result = await ctx.logic.get_variable("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_variable(self, mock_sdk):
        mock_var = AsyncMock()
        mock_sdk.logic.get_variables = AsyncMock(
            return_value=[{"id": "var-1", "name": "temperature", "value": 21.5, "_obj": mock_var}]
        )
        ctx = HomeyContext(sdk=mock_sdk)
        await ctx.logic.set_variable("temperature", 25.0)
        mock_var.set_value.assert_called_once_with(25.0)


class TestDevices:
    @pytest.mark.asyncio
    async def test_get_capability(self, mock_sdk):
        mock_device = MagicMock()
        mock_device.capabilitiesObj = {"measure_temperature": MagicMock(value=21.5)}
        mock_sdk.devices.get_device = AsyncMock(return_value=mock_device)
        ctx = HomeyContext(sdk=mock_sdk)
        result = await ctx.devices.get_capability("device-1", "measure_temperature")
        assert result == 21.5

    @pytest.mark.asyncio
    async def test_set_capability(self, mock_sdk):
        mock_device = AsyncMock()
        mock_sdk.devices.get_device = AsyncMock(return_value=mock_device)
        ctx = HomeyContext(sdk=mock_sdk)
        await ctx.devices.set_capability("device-1", "onoff", True)
        mock_device.set_capability_value.assert_called_once_with("onoff", True)


class TestFlow:
    def test_flow_context_not_available(self, mock_sdk):
        """homey.flow.trigger is not supported by the Homey Python SDK — no flow property."""
        ctx = HomeyContext(sdk=mock_sdk)
        assert not hasattr(ctx, "flow")
