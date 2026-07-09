import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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


class TestFlow:
    @pytest.mark.asyncio
    async def test_trigger_with_tag(self, mock_sdk):
        mock_card = AsyncMock()
        mock_sdk.flow.get_trigger_card = MagicMock(return_value=mock_card)
        ctx = HomeyContext(sdk=mock_sdk)
        await ctx.flow.trigger("gordijn-open")
        mock_sdk.flow.get_trigger_card.assert_called_once_with("python_triggered")
        mock_card.trigger.assert_called_once_with({}, tag="gordijn-open")

    @pytest.mark.asyncio
    async def test_trigger_no_tag(self, mock_sdk):
        mock_card = AsyncMock()
        mock_sdk.flow.get_trigger_card = MagicMock(return_value=mock_card)
        ctx = HomeyContext(sdk=mock_sdk)
        await ctx.flow.trigger()
        mock_card.trigger.assert_called_once_with({}, tag="")


class TestLogic:
    @pytest.mark.asyncio
    async def test_get_variable_found(self, mock_sdk):
        variables = {
            "id1": {"name": "zon_impact", "type": "number", "value": 42},
            "id2": {"name": "other", "type": "string", "value": "hello"},
        }
        with patch("pythonscript.homey_context._homey_rest", new=AsyncMock(return_value=variables)):
            ctx = HomeyContext(sdk=mock_sdk)
            result = await ctx.logic.get_variable("zon_impact")
        assert result == 42

    @pytest.mark.asyncio
    async def test_get_variable_not_found_returns_none(self, mock_sdk):
        variables = {"id1": {"name": "other", "type": "string", "value": "x"}}
        with patch("pythonscript.homey_context._homey_rest", new=AsyncMock(return_value=variables)):
            ctx = HomeyContext(sdk=mock_sdk)
            result = await ctx.logic.get_variable("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_variable_raises_not_supported(self, mock_sdk):
        ctx = HomeyContext(sdk=mock_sdk)
        with pytest.raises(RuntimeError, match="not supported"):
            await ctx.logic.set_variable("zon_impact", 99)


class TestDevices:
    @pytest.mark.asyncio
    async def test_get_capability_value(self, mock_sdk):
        device = {
            "capabilitiesObj": {
                "onoff": {"value": True, "lastUpdated": 123},
                "dim": {"value": 0.8, "lastUpdated": 456},
            }
        }
        with patch("pythonscript.homey_context._homey_rest", new=AsyncMock(return_value=device)):
            ctx = HomeyContext(sdk=mock_sdk)
            result = await ctx.devices.get_capability("device-uuid", "onoff")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_capability_missing_returns_none(self, mock_sdk):
        device = {"capabilitiesObj": {"onoff": {"value": False}}}
        with patch("pythonscript.homey_context._homey_rest", new=AsyncMock(return_value=device)):
            ctx = HomeyContext(sdk=mock_sdk)
            result = await ctx.devices.get_capability("device-uuid", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_capability_calls_rest(self, mock_sdk):
        mock_rest = AsyncMock(return_value=None)
        with patch("pythonscript.homey_context._homey_rest", new=mock_rest):
            ctx = HomeyContext(sdk=mock_sdk)
            await ctx.devices.set_capability("device-uuid", "onoff", False)
        mock_rest.assert_called_once_with(
            mock_sdk, "PUT",
            "/api/manager/devices/device/device-uuid/capability/onoff",
            {"value": False},
        )

    @pytest.mark.asyncio
    async def test_set_capability_numeric_value(self, mock_sdk):
        mock_rest = AsyncMock(return_value=None)
        with patch("pythonscript.homey_context._homey_rest", new=mock_rest):
            ctx = HomeyContext(sdk=mock_sdk)
            await ctx.devices.set_capability("device-uuid", "dim", 0.5)
        mock_rest.assert_called_once_with(
            mock_sdk, "PUT",
            "/api/manager/devices/device/device-uuid/capability/dim",
            {"value": 0.5},
        )
