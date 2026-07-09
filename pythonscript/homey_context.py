import asyncio
import json
import ssl
import urllib.error
import urllib.request


async def _homey_rest(sdk, method: str, path: str, body=None):
    token = await sdk.api.get_owner_api_token()
    local_url = await sdk.api.get_local_url()
    url = f"{local_url}{path}"
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    def _sync():
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_ctx))
        try:
            with opener.open(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            raise RuntimeError(f"HTTP {e.code} {method} {path}: {detail}") from None

    return await asyncio.get_running_loop().run_in_executor(None, _sync)


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
        variables = await _homey_rest(self._sdk, "GET", "/api/manager/logic/variable")
        for v in variables.values():
            if v.get("name") == name:
                return v.get("value")
        return None

    async def set_variable(self, name: str, value) -> None:
        variables = await _homey_rest(self._sdk, "GET", "/api/manager/logic/variable")
        for vid, v in variables.items():
            if v.get("name") == name:
                await _homey_rest(self._sdk, "PUT", f"/api/manager/logic/variable/{vid}", {"value": value})
                return
        raise KeyError(f"Variable '{name}' not found")


class _DevicesContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def get_capability(self, device_id: str, capability: str):
        device = await _homey_rest(self._sdk, "GET", f"/api/manager/devices/device/{device_id}")
        caps = device.get("capabilitiesObj") or {}
        cap = caps.get(capability) or {}
        return cap.get("value")

    async def set_capability(self, device_id: str, capability: str, value) -> None:
        await _homey_rest(
            self._sdk, "PUT",
            f"/api/manager/devices/device/{device_id}/capability/{capability}",
            {"value": value},
        )


class _FlowContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def trigger(self, tag: str = "") -> None:
        trigger_card = self._sdk.flow.get_trigger_card("python_triggered")
        await trigger_card.trigger({}, tag=tag)
