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


class _LogicContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def get_variable(self, name: str):
        variables = await self._sdk.api.get("/manager/logic/variable")
        for v in variables.values():
            if v.get("name") == name:
                return v.get("value")
        return None

    async def set_variable(self, name: str, value) -> None:
        variables = await self._sdk.api.get("/manager/logic/variable")
        for vid, v in variables.items():
            if v.get("name") == name:
                # SDK put() is missing internal await — double-await required
                await (await self._sdk.api.put(f"/manager/logic/variable/{vid}", {"value": value}))
                return
        raise KeyError(f"Variable '{name}' not found")


class _DevicesContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def get_capability(self, device_id: str, capability: str):
        device = await self._sdk.api.get(f"/manager/devices/device/{device_id}")
        caps = device.get("capabilitiesObj") or {}
        cap = caps.get(capability) or {}
        return cap.get("value")

    async def set_capability(self, device_id: str, capability: str, value) -> None:
        await (await self._sdk.api.put(
            f"/manager/devices/device/{device_id}/capability/{capability}",
            {"value": value},
        ))


class _FlowContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def trigger(self, tag: str = "") -> None:
        trigger_card = self._sdk.flow.get_trigger_card("python_triggered")
        await trigger_card.trigger({}, tag=tag)


