from pathlib import Path
import os
import re

from pythonscript.venv_manager import VenvManager

_VENV_ROOT = Path(os.environ.get("VENV_ROOT", "/userdata/venvs"))


async def venvs(homey, **kwargs):
    vm = VenvManager(venv_root=_VENV_ROOT)
    return vm.list_venvs()


async def delete_venv(homey, **kwargs):
    # Homey SDK nests POST body under 'body' key; try direct kwarg first
    uid = str(kwargs.get('uid') or (kwargs.get('body') or {}).get('uid') or '')
    if not uid or not re.match(r'^[\w\-]+$', uid):
        raise ValueError(f"Missing or invalid uid: {uid!r}")
    vm = VenvManager(venv_root=_VENV_ROOT)
    vm.delete(uid)
    return None
