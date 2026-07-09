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


async def build_venv(homey, **kwargs):
    body = kwargs.get('body') or {}
    name = str(body.get('name') or kwargs.get('name') or '')
    requirements = str(body.get('requirements') or kwargs.get('requirements') or '')
    if not name or not _NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid venv name: {name!r}")
    vm = VenvManager(venv_root=_VENV_ROOT)
    await vm.build(name, requirements)
    return None


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
    sm = _sm()
    code = sm.get_script(name)
    meta = sm.get_meta(name)
    return {"name": name, "code": code, "sandbox": meta.get("sandbox", True), "venv": meta.get("venv")}


async def save_script(homey, **kwargs):
    body = kwargs.get('body') or {}
    name = str(body.get('name') or kwargs.get('name') or '')
    code = str(body.get('code') or kwargs.get('code') or '')
    if not name or not _NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid script name: {name!r}")
    sandbox = body.get('sandbox')
    sandbox = True if sandbox is None else bool(sandbox)
    raw_venv = body.get('venv') or ''
    venv = str(raw_venv).strip() if raw_venv else None
    if venv and not _NAME_RE.fullmatch(venv):
        raise ValueError(f"Invalid venv name: {venv!r}")
    sm = _sm()
    sm.save_script(name, code)
    sm.save_meta(name, {"sandbox": sandbox, "venv": venv})
    return None


async def delete_script(homey, **kwargs):
    body = kwargs.get('body') or {}
    name = str(body.get('name') or kwargs.get('name') or '')
    if not name or not _NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid script name: {name!r}")
    _sm().delete_script(name)
    return None


async def exec_script(homey, **kwargs):
    """Run an inline script. Used for automated testing and CI."""
    from pythonscript.executor import Executor
    body = kwargs.get('body') or {}
    script = str(body.get('script') or '')
    args = body.get('args') or None
    timeout = min(int(body.get('timeout') or 30), 60)
    if not script:
        raise ValueError("script is required")
    executor = Executor(sdk=homey, venv_root=_VENV_ROOT)
    result = await executor.run(
        script=script,
        args=args,
        sandbox=False,
        requirements="",
        timeout=timeout,
        card_uid="_test",
    )
    return result.homey_tokens


async def run_script_api(homey, **kwargs):
    from pythonscript.executor import Executor
    body = kwargs.get('body') or {}
    name = str(body.get('name') or kwargs.get('name') or '')
    args = body.get('args') or kwargs.get('args') or None
    timeout = int(body.get('timeout') or kwargs.get('timeout') or 30)
    sandbox = body.get('sandbox')
    sandbox = True if sandbox is None else bool(sandbox)
    venv_name = str(body.get('venv') or '').strip()
    if not name or not _NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid script name: {name!r}")
    if venv_name and not _NAME_RE.fullmatch(venv_name):
        raise ValueError(f"Invalid venv name: {venv_name!r}")
    code = _sm().get_script(name)
    executor = Executor(sdk=homey, venv_root=_VENV_ROOT)
    result = await executor.run(
        script=code,
        args=args,
        sandbox=sandbox,
        requirements="",
        timeout=timeout,
        card_uid=venv_name if not sandbox else "sandboxed",
    )
    return result.homey_tokens
