from pathlib import Path
import os

from pythonscript.venv_manager import VenvManager

_VENV_ROOT = Path(os.environ.get("VENV_ROOT", "/userdata/venvs"))


async def venvs(homey, **kwargs):
    vm = VenvManager(venv_root=_VENV_ROOT)
    return vm.list_venvs()


async def delete_venv(homey, uid, **kwargs):
    vm = VenvManager(venv_root=_VENV_ROOT)
    vm.delete(uid)
    return None
