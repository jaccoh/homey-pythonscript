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
    async def test_trigger_with_tokens(self, mock_sdk):
        mock_card = AsyncMock()
        mock_sdk.flow.get_trigger_card = MagicMock(return_value=mock_card)
        ctx = HomeyContext(sdk=mock_sdk)
        await ctx.flow.trigger("my-tag", tokens={"result": "42"})
        mock_card.trigger.assert_called_once_with({"result": "42"}, tag="my-tag")

    @pytest.mark.asyncio
    async def test_trigger_no_tag(self, mock_sdk):
        mock_card = AsyncMock()
        mock_sdk.flow.get_trigger_card = MagicMock(return_value=mock_card)
        ctx = HomeyContext(sdk=mock_sdk)
        await ctx.flow.trigger()
        mock_card.trigger.assert_called_once_with({}, tag="")
