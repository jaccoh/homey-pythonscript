import asyncio
import hashlib
import shutil
import sys
import subprocess
import tempfile
from pathlib import Path


class VenvManager:
    def __init__(self, venv_root: Path):
        self._root = Path(venv_root)
        self._locks: dict[str, asyncio.Lock] = {}

    def _hash(self, requirements: str) -> str:
        return hashlib.sha256(requirements.strip().encode()).hexdigest()

    def _hash_file(self, card_uid: str) -> Path:
        return self._root / card_uid / ".requirements_hash"

    def _write_hash(self, card_uid: str, requirements: str) -> None:
        (self._root / card_uid).mkdir(parents=True, exist_ok=True)
        self._hash_file(card_uid).write_text(self._hash(requirements))

    def _lock(self, card_uid: str) -> asyncio.Lock:
        if card_uid not in self._locks:
            self._locks[card_uid] = asyncio.Lock()
        return self._locks[card_uid]

    def needs_rebuild(self, card_uid: str, requirements: str) -> bool:
        hf = self._hash_file(card_uid)
        if not hf.exists():
            return True
        return hf.read_text() != self._hash(requirements)

    def delete(self, card_uid: str) -> None:
        target = self._root / card_uid
        if target.exists():
            shutil.rmtree(target)

    def list_venvs(self) -> list[dict]:
        if not self._root.exists():
            return []
        entries = []
        for d in self._root.iterdir():
            if not d.is_dir():
                continue
            hf = d / ".requirements_hash"
            entries.append({
                "name": d.name,
                "hash": hf.read_text() if hf.exists() else None,
            })
        return entries

    def venv_path(self, card_uid: str) -> Path:
        return self._root / card_uid

    async def build(self, card_uid: str, requirements: str) -> None:
        """pip install requirements into venvs/{card_uid}/. Raises on failure."""
        async with self._lock(card_uid):
            await self._build_unlocked(card_uid, requirements)

    async def _build_unlocked(self, card_uid: str, requirements: str) -> None:
        """Inner build logic; must only be called while holding _lock(card_uid)."""
        venv_dir = self.venv_path(card_uid)
        venv_dir.mkdir(parents=True, exist_ok=True)
        run = asyncio.get_running_loop().run_in_executor
        try:
            await run(None, lambda: subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)], check=True, capture_output=True
            ))
            pip = venv_dir / "bin" / "pip"
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write(requirements.strip())
                req_file = f.name
            try:
                await run(None, lambda: subprocess.run(
                    [str(pip), "install", "-r", req_file], check=True, capture_output=True
                ))
            finally:
                Path(req_file).unlink(missing_ok=True)
            self._write_hash(card_uid, requirements)
        except Exception:
            shutil.rmtree(venv_dir, ignore_errors=True)
            raise
