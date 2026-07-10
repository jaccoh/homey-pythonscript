import textwrap

_BRIDGE_SOURCE = '''
import sys as _sys
import json as _json
import asyncio as _asyncio
import threading as _threading

_real_stdout = _sys.stdout
_sys.stdout = _sys.stderr

_rpc_lock = _threading.Lock()


def _send(msg: dict) -> None:
    _real_stdout.write(_json.dumps(msg) + "\\n")
    _real_stdout.flush()


def _recv() -> dict:
    return _json.loads(_sys.stdin.readline())


class HomeyBridge:
    def set_tag(self, name: str, value) -> None:
        _send({"type": "set_tag", "name": name, "value": value})

    @property
    def logic(self):
        return _LogicBridge(self)

    @property
    def devices(self):
        return _DevicesBridge(self)

    @property
    def flow(self):
        return _FlowBridge(self)

    def _rpc(self, method: str, args: list):
        with _rpc_lock:
            _send({"type": "call", "method": method, "args": args})
            response = _recv()
        if "error" in response:
            raise RuntimeError(response["error"])
        return response["result"]

    async def _arpc(self, method: str, args: list):
        loop = _asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._rpc, method, args)


class _LogicBridge:
    def __init__(self, bridge):
        self._b = bridge

    async def get_variable(self, name: str):
        return await self._b._arpc("logic.get_variable", [name])

    async def set_variable(self, name: str, value) -> None:
        await self._b._arpc("logic.set_variable", [name, value])


class _DevicesBridge:
    def __init__(self, bridge):
        self._b = bridge

    async def get_capability(self, device_id: str, capability: str):
        return await self._b._arpc("devices.get_capability", [device_id, capability])

    async def set_capability(self, device_id: str, capability: str, value) -> None:
        await self._b._arpc("devices.set_capability", [device_id, capability, value])


class _FlowBridge:
    def __init__(self, bridge):
        self._b = bridge

    async def trigger(self, tag: str = "") -> None:
        await self._b._arpc("flow.trigger", [tag])


homey = HomeyBridge()
'''

_SANDBOX_BRIDGE_SOURCE = '''
import sys as _sys, json as _json
_real_stdout = _sys.stdout
_sys.stdout = _sys.stderr


def _send(msg):
    _real_stdout.write(_json.dumps(msg) + "\\n")
    _real_stdout.flush()


class HomeyBridge:
    def set_tag(self, name, value):
        _send({"type": "set_tag", "name": name, "value": value})

    @property
    def logic(self):
        raise RuntimeError(
            "homey.logic not available in sandboxed mode. "
            "Use the non-sandboxed Run Script with Packages card."
        )

    @property
    def devices(self):
        raise RuntimeError(
            "homey.devices not available in sandboxed mode. "
            "Use the non-sandboxed Run Script with Packages card."
        )

    @property
    def flow(self):
        raise RuntimeError(
            "homey.flow not available in sandboxed mode. "
            "Use the non-sandboxed Run Script with Packages card."
        )


homey = HomeyBridge()
'''

_RUNNER_TEMPLATE = '''
args = {args_repr}


async def _run():
{user_body}


async def _main():
    try:
        result = await _run()
        _send({{"type": "return", "value": result}})
    except Exception as _e:
        import traceback as _tb
        _send({{"type": "error", "message": str(_e), "traceback": _tb.format_exc()}})


_asyncio.run(_main())
'''


_SANDBOX_RUNNER = '''
import operator as _op
from RestrictedPython import compile_restricted_function as _crf, safe_builtins as _sb
from RestrictedPython.Guards import safer_getattr as _sga, full_write_guard as _fwg

_ALLOWED = frozenset({{
    "math", "json", "datetime", "re", "collections", "itertools",
    "functools", "string", "decimal", "fractions", "statistics",
}})


def _restricted_import(name, *args, **kwargs):
    if name.split(".")[0] not in _ALLOWED:
        raise Exception(f"import '{{name}}' not allowed in sandboxed mode")
    return __import__(name, *args, **kwargs)


def _safe_getattr(obj, name, *args):
    if isinstance(name, str) and name.startswith("_"):
        raise AttributeError(f"access to '{{name}}' not allowed")
    return _sga(obj, name, *args) if args else _sga(obj, name)


def _blocked(*args, **kwargs):
    raise Exception("not allowed in sandboxed mode")


_bi = dict(_sb)
_bi["__import__"] = _restricted_import
for _bname in ("open", "exec", "eval", "compile"):
    _bi[_bname] = _blocked

args = {args_repr}
_body = {script_repr}
_compiled = _crf(p="homey, args", body=_body, name="script_fn", filename="<script>")

try:
    if _compiled.errors:
        _msg = "; ".join(_compiled.errors)
        _exc = SyntaxError if any(": SyntaxError:" in e for e in _compiled.errors) else Exception
        raise _exc(_msg)
    _ns = {{
        "__builtins__": _bi,
        "_getattr_": _safe_getattr,
        "_getitem_": _op.getitem,
        "_getiter_": iter,
        "_write_": _fwg,
    }}
    exec(_compiled.code, _ns)
    _result = _ns["script_fn"](homey, args)
    _send({{"type": "return", "value": _result}})
except Exception as _e:
    import traceback as _tb
    _send({{"type": "error", "message": str(_e), "traceback": _tb.format_exc()}})
'''


def generate_wrapper(script: str, args) -> str:
    user_body = textwrap.indent(textwrap.dedent(script), "    ")
    tail = _RUNNER_TEMPLATE.format(
        args_repr=repr(args),
        user_body=user_body,
    )
    return _BRIDGE_SOURCE + tail


def generate_sandbox_wrapper(script: str, args) -> str:
    return _SANDBOX_BRIDGE_SOURCE + _SANDBOX_RUNNER.format(
        args_repr=repr(args),
        script_repr=repr(script),
    )
