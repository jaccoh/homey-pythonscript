import asyncio
import hashlib
import shutil
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import ClassVar


class VenvManager:
    _locks: ClassVar[dict[str, asyncio.Lock]] = {}

    def __init__(self, venv_root: Path):
        self._root = Path(venv_root)

    def _hash(self, requirements: str) -> str:
        return hashlib.sha256(requirements.strip().encode()).hexdigest()

    def _hash_file(self, card_uid: str) -> Path:
        return self._root / card_uid / ".requirements_hash"

    def _requirements_file(self, card_uid: str) -> Path:
        return self._root / card_uid / ".requirements.txt"

    def _write_hash(self, card_uid: str, requirements: str) -> None:
        (self._root / card_uid).mkdir(parents=True, exist_ok=True)
        self._hash_file(card_uid).write_text(self._hash(requirements))
        self._requirements_file(card_uid).write_text(requirements.strip())

    def _lock(self, card_uid: str) -> asyncio.Lock:
        if card_uid not in VenvManager._locks:
            VenvManager._locks[card_uid] = asyncio.Lock()
        return VenvManager._locks[card_uid]

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
            rf = d / ".requirements.txt"
            entries.append({
                "name": d.name,
                "hash": hf.read_text() if hf.exists() else None,
                "requirements": rf.read_text() if rf.exists() else "",
            })
        return entries

    def venv_path(self, card_uid: str) -> Path:
        p = (self._root / card_uid).resolve()
        if not p.is_relative_to(self._root.resolve()):
            raise ValueError(f"Invalid venv name: {card_uid!r}")
        return p

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
            except subprocess.CalledProcessError as e:
                stderr = (e.stderr or b"").decode(errors="replace").strip()
                stdout = (e.stdout or b"").decode(errors="replace").strip()
                detail = stderr or stdout or f"exit code {e.returncode}"
                raise RuntimeError(f"pip install failed:\n{detail}") from None
            finally:
                Path(req_file).unlink(missing_ok=True)
        except Exception:
            shutil.rmtree(venv_dir, ignore_errors=True)
            raise
        # hash write outside try/except — failure here doesn't destroy the venv
        self._write_hash(card_uid, requirements)
