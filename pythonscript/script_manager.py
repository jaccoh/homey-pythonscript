import json
import re
from pathlib import Path


_NAME_RE = re.compile(r'^[\w\-]+$')


class ScriptManager:
    def __init__(self, scripts_root: Path):
        self._root = Path(scripts_root)

    def _validate_name(self, name: str) -> None:
        if not _NAME_RE.fullmatch(name):
            raise ValueError(f"Invalid script name: {name!r}")

    def script_path(self, name: str) -> Path:
        self._validate_name(name)
        return self._root / f"{name}.py"

    def meta_path(self, name: str) -> Path:
        self._validate_name(name)
        return self._root / f"{name}.json"

    def get_meta(self, name: str) -> dict:
        self._validate_name(name)
        p = self.meta_path(name)
        if not p.exists():
            return {"sandbox": True, "venv": None}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"sandbox": True, "venv": None}

    def save_meta(self, name: str, meta: dict) -> None:
        self._validate_name(name)
        self._root.mkdir(parents=True, exist_ok=True)
        self.meta_path(name).write_text(json.dumps(meta), encoding="utf-8")

    def list_scripts(self) -> list[dict]:
        if not self._root.exists():
            return []
        return [
            {"name": p.stem, "size": p.stat().st_size}
            for p in sorted(self._root.glob("*.py"))
        ]

    def get_script(self, name: str) -> str:
        self._validate_name(name)
        path = self.script_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Script not found: {name}")
        return path.read_text(encoding="utf-8")

    def save_script(self, name: str, code: str) -> None:
        self._validate_name(name)
        self._root.mkdir(parents=True, exist_ok=True)
        self.script_path(name).write_text(code, encoding="utf-8")

    def delete_script(self, name: str) -> None:
        self._validate_name(name)
        self.script_path(name).unlink(missing_ok=True)
        self.meta_path(name).unlink(missing_ok=True)
