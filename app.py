import os
import sys
from pathlib import Path

# Homey runner may not include the app directory in sys.path.
sys.path.insert(0, str(Path(__file__).parent))

from homey import app as homey_app  # noqa: E402

from pythonscript.executor import Executor  # noqa: E402
from pythonscript.venv_manager import VenvManager  # noqa: E402

_VENV_ROOT = Path(os.environ.get("VENV_ROOT", "/userdata/venvs"))
_DEFAULT_TIMEOUT = 30


class PythonScriptApp(homey_app.App):
    async def on_init(self) -> None:
        self.log("PythonScriptApp initialised")
        self._vm = VenvManager(venv_root=_VENV_ROOT)
        self._executor = Executor(sdk=self.homey, venv_root=_VENV_ROOT)

        run_card = self.homey.flow.get_action_card("run_script")
        run_card.register_run_listener(self._on_run_script)

        run_arg_card = self.homey.flow.get_action_card("run_script_with_argument")
        run_arg_card.register_run_listener(self._on_run_script_with_argument)

        # Homey Python SDK does not expose a card-save hook (unlike JS SDK's .on("update")).
        # Venv pre-baking is deferred to first execution (_execute), ensuring lazy rebuild
        # only when the script actually runs. Future SDK updates may enable card-save hooks.

        # Settings API (GET /venvs, DELETE /venvs/{uid}) not registered here:
        # the Homey Python SDK does not expose self.homey.api in Python the way the JS SDK
        # does (this.homey.api.registerGetHandler / registerDeleteHandler).
        # The settings/index.html page calls Homey.api() via the homey-settings-client JS
        # library, which routes through the Homey cloud/local runtime directly — no Python
        # handler registration is needed on this side.

    async def _on_run_script(self, card_arguments, **_) -> dict:
        return await self._execute(card_arguments, args=None)

    async def _on_run_script_with_argument(self, card_arguments, **_) -> dict:
        return await self._execute(card_arguments, args=card_arguments.get("argument"))

    async def _execute(self, card_arguments: dict, args) -> dict:
        script = card_arguments.get("script", "")
        requirements = card_arguments.get("requirements", "") or ""
        sandbox = card_arguments.get("sandbox", True)
        timeout = int(card_arguments.get("timeout") or _DEFAULT_TIMEOUT)
        card_uid = card_arguments.get("_uid", "default")

        if requirements and self._vm.needs_rebuild(card_uid, requirements):
            self.log(f"Building venv for card {card_uid}")
            await self._vm.build(card_uid, requirements)

        result = await self._executor.run(
            script=script,
            args=args,
            sandbox=sandbox,
            requirements=requirements,
            timeout=timeout,
            card_uid=card_uid,
        )
        return result.homey_tokens


homey_export = PythonScriptApp
