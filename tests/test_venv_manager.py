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


import asyncio
import pytest


@pytest.mark.asyncio
async def test_concurrent_builds_serialize(tmp_venv_dir):
    """Two concurrent builds for same uid must serialize via Lock."""
    vm = VenvManager(venv_root=tmp_venv_dir)
    call_log = []

    async def fake_build():
        async with vm._lock("test-uid"):
            call_log.append("start")
            await asyncio.sleep(0.02)
            call_log.append("end")

    await asyncio.gather(fake_build(), fake_build())

    # With lock: ['start', 'end', 'start', 'end']
    # Without lock: ['start', 'start', 'end', 'end']
    assert call_log[1] == "end", f"Lock did not serialize: {call_log}"


@pytest.mark.asyncio
async def test_different_uids_do_not_block(tmp_venv_dir):
    """Builds for different uids must not block each other."""
    vm = VenvManager(venv_root=tmp_venv_dir)
    call_log = []

    async def fake_build(uid):
        async with vm._lock(uid):
            call_log.append(f"start:{uid}")
            await asyncio.sleep(0.02)
            call_log.append(f"end:{uid}")

    await asyncio.gather(fake_build("uid-a"), fake_build("uid-b"))

    # Both should interleave freely (start:a, start:b before end:a or end:b)
    starts = [i for i, x in enumerate(call_log) if x.startswith("start")]
    assert len(starts) == 2, f"Expected 2 starts, got: {call_log}"
    # The two starts should appear before either end (interleaved, not serialized)
    first_end = next(i for i, x in enumerate(call_log) if x.startswith("end"))
    assert starts[1] < first_end, f"Different uids serialized unexpectedly: {call_log}"


class TestVenvManagerList:
    def test_list_returns_names(self, tmp_venv_dir):
        vm = VenvManager(venv_root=tmp_venv_dir)
        (tmp_venv_dir / "card-1").mkdir()
        vm._write_hash("card-1", "requests==2.31.0")
        (tmp_venv_dir / "card-2").mkdir()
        vm._write_hash("card-2", "numpy>=1.26")
        entries = vm.list_venvs()
        assert {e["name"] for e in entries} == {"card-1", "card-2"}
