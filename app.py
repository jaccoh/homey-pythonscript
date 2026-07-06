import os
import re
import sys
from pathlib import Path

# Homey runner may not include the app directory in sys.path.
sys.path.insert(0, str(Path(__file__).parent))

from homey import app as homey_app  # noqa: E402

from pythonscript.executor import Executor  # noqa: E402
from pythonscript.venv_manager import VenvManager  # noqa: E402

_VENV_ROOT = Path(os.environ.get("VENV_ROOT", "/userdata/venvs"))
_DEFAULT_TIMEOUT = 30
_VENV_NAME_RE = re.compile(r'^[\w\-]+$')


class PythonScriptApp(homey_app.App):
    async def on_init(self) -> None:
        self.log("PythonScriptApp initialised")
        self._vm = VenvManager(venv_root=_VENV_ROOT)
        self._executor = Executor(sdk=self.homey, venv_root=_VENV_ROOT)

        # Card 1: Run Script — sandboxed, optional arg, no requirements
        sandboxed_card = self.homey.flow.get_action_card("run_script")
        sandboxed_card.register_run_listener(self._on_run_sandboxed)

        # Card 2: Run Script with Packages — Runner, optional arg, requirements + venv
        packages_card = self.homey.flow.get_action_card("run_script_with_argument")
        packages_card.register_run_listener(self._on_run_with_packages)
        packages_card.get_argument("venv_name").register_autocomplete_listener(
            self._autocomplete_venv_name
        )

    async def _autocomplete_venv_name(self, query, **_):
        existing = [v["name"] for v in self._vm.list_venvs()]
        results = [
            {"name": name, "description": "existing environment"}
            for name in existing
            if not query or query.lower() in name.lower()
        ]
        if query and _VENV_NAME_RE.match(query) and query not in existing:
            results.insert(0, {"name": query, "description": "create new environment"})
        return results

    async def _on_run_sandboxed(self, card_arguments, **_) -> dict:
        script = card_arguments.get("script", "")
        args = card_arguments.get("argument") or None
        timeout = int(card_arguments.get("timeout") or _DEFAULT_TIMEOUT)

        result = await self._executor.run(
            script=script,
            args=args,
            sandbox=True,
            requirements="",
            timeout=timeout,
            card_uid="sandboxed",
        )
        return result.homey_tokens

    async def _on_run_with_packages(self, card_arguments, **_) -> dict:
        script = card_arguments.get("script", "")
        args = card_arguments.get("argument") or None
        requirements = card_arguments.get("requirements", "") or ""
        timeout = int(card_arguments.get("timeout") or _DEFAULT_TIMEOUT)

        raw_venv = card_arguments.get("venv_name") or ""
        if isinstance(raw_venv, dict):
            raw_venv = raw_venv.get("name", "")
        card_uid = str(raw_venv).strip() or "default"

        if requirements and self._vm.needs_rebuild(card_uid, requirements):
            self.log(f"Building venv '{card_uid}'")
            await self._vm.build(card_uid, requirements)

        result = await self._executor.run(
            script=script,
            args=args,
            sandbox=False,
            requirements=requirements,
            timeout=timeout,
            card_uid=card_uid,
        )
        return result.homey_tokens


homey_export = PythonScriptApp
