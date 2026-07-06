from pathlib import Path
import os
import re

from pythonscript.venv_manager import VenvManager

_VENV_ROOT = Path(os.environ.get("VENV_ROOT", "/userdata/venvs"))


async def venvs(homey, **kwargs):
    vm = VenvManager(venv_root=_VENV_ROOT)
    return vm.list_venvs()


async def delete_venv(homey, **kwargs):
    # Homey SDK may nest body under 'body' key or pass directly
    uid = (kwargs.get('uid')
           or (kwargs.get('body') or {}).get('uid')
           or '')
    if not uid or not re.match(r'^[\w\-]+$', str(uid)):
        raise ValueError(f"Invalid uid: {uid!r} (kwargs={list(kwargs.keys())})")
    vm = VenvManager(venv_root=_VENV_ROOT)
    vm.delete(str(uid))
    return None
