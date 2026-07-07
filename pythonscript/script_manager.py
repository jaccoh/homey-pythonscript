from pathlib import Path


class ScriptManager:
    def __init__(self, scripts_root: Path):
        self._root = Path(scripts_root)

    def script_path(self, name: str) -> Path:
        return self._root / f"{name}.py"

    def list_scripts(self) -> list[dict]:
        if not self._root.exists():
            return []
        return [
            {"name": p.stem, "size": p.stat().st_size}
            for p in sorted(self._root.glob("*.py"))
        ]

    def get_script(self, name: str) -> str:
        path = self.script_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Script not found: {name}")
        return path.read_text()

    def save_script(self, name: str, code: str) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        self.script_path(name).write_text(code)

    def delete_script(self, name: str) -> None:
        path = self.script_path(name)
        if path.exists():
            path.unlink()
