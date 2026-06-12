import pytest
from pathlib import Path
from pythonscript.venv_manager import VenvManager


class TestVenvManagerHash:
    def test_same_requirements_same_hash(self, tmp_venv_dir):
        vm = VenvManager(venv_root=tmp_venv_dir)
        assert vm._hash("requests==2.31.0\nnumpy>=1.26") == vm._hash("requests==2.31.0\nnumpy>=1.26")

    def test_different_requirements_different_hash(self, tmp_venv_dir):
        vm = VenvManager(venv_root=tmp_venv_dir)
        assert vm._hash("requests==2.31.0") != vm._hash("requests==2.30.0")

    def test_whitespace_normalised(self, tmp_venv_dir):
        vm = VenvManager(venv_root=tmp_venv_dir)
        assert vm._hash("requests==2.31.0\n") == vm._hash("requests==2.31.0")


class TestVenvManagerNeedsRebuild:
    def test_no_venv_needs_rebuild(self, tmp_venv_dir):
        vm = VenvManager(venv_root=tmp_venv_dir)
        assert vm.needs_rebuild("card-123", "requests==2.31.0") is True

    def test_same_hash_no_rebuild(self, tmp_venv_dir):
        vm = VenvManager(venv_root=tmp_venv_dir)
        vm._write_hash("card-123", "requests==2.31.0")
        assert vm.needs_rebuild("card-123", "requests==2.31.0") is False

    def test_changed_hash_needs_rebuild(self, tmp_venv_dir):
        vm = VenvManager(venv_root=tmp_venv_dir)
        vm._write_hash("card-123", "requests==2.31.0")
        assert vm.needs_rebuild("card-123", "requests==2.30.0") is True


class TestVenvManagerDelete:
    def test_delete_removes_venv_and_hash(self, tmp_venv_dir):
        vm = VenvManager(venv_root=tmp_venv_dir)
        venv_path = tmp_venv_dir / "card-123"
        venv_path.mkdir()
        vm._write_hash("card-123", "requests==2.31.0")
        vm.delete("card-123")
        assert not venv_path.exists()
        assert vm.needs_rebuild("card-123", "requests==2.31.0") is True

    def test_delete_nonexistent_is_noop(self, tmp_venv_dir):
        vm = VenvManager(venv_root=tmp_venv_dir)
        vm.delete("card-does-not-exist")  # must not raise


class TestVenvManagerList:
    def test_list_returns_card_uids(self, tmp_venv_dir):
        vm = VenvManager(venv_root=tmp_venv_dir)
        (tmp_venv_dir / "card-1").mkdir()
        vm._write_hash("card-1", "requests==2.31.0")
        (tmp_venv_dir / "card-2").mkdir()
        vm._write_hash("card-2", "numpy>=1.26")
        entries = vm.list_venvs()
        assert {e["card_uid"] for e in entries} == {"card-1", "card-2"}
