from dataclasses import dataclass, field
from pathlib import Path

from pythonscript.runner import Runner
from pythonscript.venv_manager import VenvManager


@dataclass
class ExecutionResult:
    return_value: object
    tags: dict = field(default_factory=dict)

    @property
    def homey_tokens(self) -> dict:
        tokens = {
            "return_value": str(self.return_value) if self.return_value is not None else "",
            "error": "",
        }
        tokens.update({k: str(v) for k, v in self.tags.items()})
        return tokens


class Executor:
    def __init__(self, sdk, venv_root: Path):
        self._sdk = sdk
        self._vm = VenvManager(venv_root=venv_root)

    async def run(
        self,
        script: str,
        args,
        sandbox: bool,
        requirements: str,
        timeout: int,
        card_uid: str,
    ) -> ExecutionResult:
        has_requirements = bool(requirements.strip())
        venv_path = (
            self._vm.venv_path(card_uid)
            if (has_requirements or (not sandbox and card_uid))
            else None
        )
        runner = Runner(sdk=self._sdk)
        raw = await runner.run(
            script=script,
            args=args,
            timeout=timeout,
            venv_path=venv_path,
            sandboxed=sandbox,
        )
        return ExecutionResult(
            return_value=raw["return_value"],
            tags=raw.get("tags", {}),
        )
