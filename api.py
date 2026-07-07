from pathlib import Path
import os
import re

from pythonscript.venv_manager import VenvManager
from pythonscript.script_manager import ScriptManager

_VENV_ROOT = Path(os.environ.get("VENV_ROOT", "/userdata/venvs"))
_SCRIPTS_ROOT = Path(os.environ.get("SCRIPTS_ROOT", "/userdata/scripts"))

_NAME_RE = re.compile(r'^[\w\-]+$')


def _sm() -> ScriptManager:
    return ScriptManager(scripts_root=_SCRIPTS_ROOT)


async def venvs(homey, **kwargs):
    vm = VenvManager(venv_root=_VENV_ROOT)
    return vm.list_venvs()


async def delete_venv(homey, **kwargs):
    # Homey SDK nests POST body under 'body' key; try direct kwarg first
    uid = str(kwargs.get('uid') or (kwargs.get('body') or {}).get('uid') or '')
    if not uid or not _NAME_RE.fullmatch(uid):
        raise ValueError(f"Missing or invalid uid: {uid!r}")
    vm = VenvManager(venv_root=_VENV_ROOT)
    vm.delete(uid)
    return None


async def scripts(homey, **kwargs):
    return _sm().list_scripts()


async def get_script(homey, **kwargs):
    body = kwargs.get('body') or {}
    name = str(body.get('name') or kwargs.get('name') or '')
    if not name or not _NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid script name: {name!r}")
    code = _sm().get_script(name)
    return {"name": name, "code": code}


async def save_script(homey, **kwargs):
    body = kwargs.get('body') or {}
    name = str(body.get('name') or kwargs.get('name') or '')
    code = str(body.get('code') or kwargs.get('code') or '')
    if not name or not _NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid script name: {name!r}")
    _sm().save_script(name, code)
    return None


async def delete_script(homey, **kwargs):
    body = kwargs.get('body') or {}
    name = str(body.get('name') or kwargs.get('name') or '')
    if not name or not _NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid script name: {name!r}")
    _sm().delete_script(name)
    return None


async def run_script_api(homey, **kwargs):
    """Run a named script from the settings page IDE (sandboxed)."""
    from pythonscript.executor import Executor
    body = kwargs.get('body') or {}
    name = str(body.get('name') or kwargs.get('name') or '')
    args = body.get('args') or kwargs.get('args') or None
    timeout = int(body.get('timeout') or kwargs.get('timeout') or 30)
    if not name or not _NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid script name: {name!r}")
    code = _sm().get_script(name)
    executor = Executor(sdk=homey, venv_root=_VENV_ROOT)
    result = await executor.run(
        script=code,
        args=args,
        sandbox=True,
        requirements="",
        timeout=timeout,
        card_uid="sandboxed",
    )
    return result.homey_tokens
