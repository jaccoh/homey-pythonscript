class HomeyContext:
    def __init__(self, sdk):
        self._sdk = sdk
        self._tags: dict = {}

    def set_tag(self, name: str, value) -> None:
        self._tags[name] = value

    @property
    def flow(self):
        return _FlowContext(self._sdk)

class _FlowContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def trigger(self, tag: str = "") -> None:
        trigger_card = self._sdk.flow.get_trigger_card("python_triggered")
        await trigger_card.trigger({}, tag=tag)


