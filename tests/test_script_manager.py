import pytest
from pathlib import Path
from pythonscript.script_manager import ScriptManager


@pytest.fixture
def tmp_scripts(tmp_path):
    return ScriptManager(scripts_root=tmp_path)


def test_list_empty(tmp_scripts):
    assert tmp_scripts.list_scripts() == []


def test_save_and_list(tmp_scripts):
    tmp_scripts.save_script("hello", "return 42")
    entries = tmp_scripts.list_scripts()
    assert len(entries) == 1
    assert entries[0]["name"] == "hello"
    assert "size" in entries[0]


def test_get_script(tmp_scripts):
    tmp_scripts.save_script("hello", "return 42")
    assert tmp_scripts.get_script("hello") == "return 42"


def test_get_missing_raises(tmp_scripts):
    with pytest.raises(FileNotFoundError):
        tmp_scripts.get_script("nonexistent")


def test_delete_script(tmp_scripts):
    tmp_scripts.save_script("hello", "return 42")
    tmp_scripts.delete_script("hello")
    assert tmp_scripts.list_scripts() == []


def test_delete_nonexistent_noop(tmp_scripts):
    tmp_scripts.delete_script("nonexistent")  # no exception


def test_list_returns_only_py_files(tmp_scripts):
    tmp_scripts.save_script("a", "pass")
    (tmp_scripts.script_path("a").parent / "not_a_script.txt").write_text("x")
    assert len(tmp_scripts.list_scripts()) == 1


def test_scripts_root_missing_returns_empty():
    sm = ScriptManager(scripts_root=Path("/nonexistent/path"))
    assert sm.list_scripts() == []


def test_invalid_name_raises(tmp_scripts):
    with pytest.raises(ValueError):
        tmp_scripts.save_script("../evil", "pass")


def test_name_with_dot_raises(tmp_scripts):
    with pytest.raises(ValueError):
        tmp_scripts.save_script("foo.bar", "pass")


def test_get_meta_defaults(tmp_scripts):
    tmp_scripts.save_script("s", "pass")
    meta = tmp_scripts.get_meta("s")
    assert meta == {"sandbox": True, "venv": None}


def test_save_and_get_meta(tmp_scripts):
    tmp_scripts.save_script("s", "pass")
    tmp_scripts.save_meta("s", {"sandbox": False, "venv": "my-env"})
    meta = tmp_scripts.get_meta("s")
    assert meta["sandbox"] is False
    assert meta["venv"] == "my-env"


def test_get_meta_missing_file_returns_defaults(tmp_scripts):
    meta = tmp_scripts.get_meta("nonexistent_but_valid_name")
    assert meta == {"sandbox": True, "venv": None}


def test_delete_removes_meta(tmp_scripts):
    tmp_scripts.save_script("s", "pass")
    tmp_scripts.save_meta("s", {"sandbox": False, "venv": "e"})
    tmp_scripts.delete_script("s")
    assert not tmp_scripts.meta_path("s").exists()


def test_list_ignores_json_files(tmp_scripts):
    tmp_scripts.save_script("s", "pass")
    tmp_scripts.save_meta("s", {"sandbox": True, "venv": None})
    assert len(tmp_scripts.list_scripts()) == 1
