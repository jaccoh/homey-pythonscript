import textwrap

_BRIDGE_SOURCE = '''
import sys as _sys
import json as _json
import asyncio as _asyncio

_real_stdout = _sys.stdout
_sys.stdout = _sys.stderr


def _send(msg: dict) -> None:
    _real_stdout.write(_json.dumps(msg) + "\\n")
    _real_stdout.flush()


def _recv() -> dict:
    return _json.loads(_sys.stdin.readline())


class HomeyBridge:
    def set_tag(self, name: str, value) -> None:
        _send({"type": "set_tag", "name": name, "value": value})

    @property
    def flow(self):
        return _FlowBridge(self)

    def _rpc(self, method: str, args: list):
        _send({"type": "call", "method": method, "args": args})
        response = _recv()
        if "error" in response:
            raise RuntimeError(response["error"])
        return response["result"]

    async def _arpc(self, method: str, args: list):
        loop = _asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._rpc, method, args)


class _FlowBridge:
    def __init__(self, bridge):
        self._b = bridge

    async def trigger(self, tag: str = "") -> None:
        await self._b._arpc("flow.trigger", [tag])


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


def generate_wrapper(script: str, args) -> str:
    user_body = textwrap.indent(textwrap.dedent(script), "    ")
    tail = _RUNNER_TEMPLATE.format(
        args_repr=repr(args),
        user_body=user_body,
    )
    return _BRIDGE_SOURCE + tail
