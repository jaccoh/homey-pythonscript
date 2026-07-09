class HomeyContext:
    def __init__(self, sdk):
        self._sdk = sdk
        self._tags: dict = {}

    def set_tag(self, name: str, value) -> None:
        self._tags[name] = value

    @property
    def logic(self):
        return _LogicContext(self._sdk)

    @property
    def devices(self):
        return _DevicesContext(self._sdk)

    @property
    def flow(self):
        return _FlowContext(self._sdk)

class _FlowContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def trigger(self, tag: str = "", tokens: dict = None) -> None:
        trigger_card = self._sdk.flow.get_trigger_card("python_triggered")
        await trigger_card.trigger(tokens or {}, tag=tag)


class _LogicContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def get_variable(self, name: str):
        variables = await self._sdk.logic.get_variables()
        for v in variables:
            if v["name"] == name:
                return v["value"]
        return None

    async def set_variable(self, name: str, value) -> None:
        variables = await self._sdk.logic.get_variables()
        for v in variables:
            if v["name"] == name:
                await v["_obj"].set_value(value)
                return
        raise KeyError(f"Variable '{name}' not found")


class _DevicesContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def get_capability(self, device_id: str, capability: str):
        device = await self._sdk.devices.get_device(device_id)
        return device.capabilitiesObj[capability].value

    async def set_capability(self, device_id: str, capability: str, value) -> None:
        device = await self._sdk.devices.get_device(device_id)
        await device.set_capability_value(capability, value)


