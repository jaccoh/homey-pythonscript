# homey-pythonscript Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Homey Python SDK app with two action cards (Run Script, Run Script with Argument) that execute Python code from Advanced Flows, with sandboxed and full-Python execution tiers, venv pre-baking, and real-time Homey API access.

**Architecture:** Two execution tiers: (1) RestrictedPython runs in-process with direct SDK access via a `HomeyContext` object; (2) Full Python runs in a subprocess with a `HomeyBridge` object that communicates to the parent over stdin/stdout JSON protocol. Both tiers share the same card UX. Venvs are pre-baked at card-save time and keyed by card UID. User print() output is captured from subprocess stderr; the protocol uses stdout.

**Tech Stack:** Python 3.14, Homey Python SDK (`from homey import app`), RestrictedPython >=7.0, pytest, asyncio.

---

## File Map

```
homey-pythonscript/
├── app.py                                  # App class, registers card handlers, venv pre-bake on save
├── app.json                                # Homey manifest (runtime: python, sdk: 3)
├── .homeycompose/
│   └── flow/
│       └── actions/
│           ├── run_script.json             # "Run Script" card (no argument)
│           └── run_script_with_argument.json  # "Run Script with Argument" card
├── pythonscript/
│   ├── __init__.py
│   ├── executor.py                         # Routes to sandbox or subprocess runner; returns result dict
│   ├── sandbox.py                          # RestrictedPython in-process execution
│   ├── runner.py                           # asyncio subprocess execution with JSON-lines IPC
│   ├── venv_manager.py                     # Venv lifecycle: hash-check, pip install, delete, list
│   ├── homey_context.py                    # homey object for sandboxed tier (direct SDK calls)
│   ├── homey_bridge.py                     # homey object bundled into subprocess wrapper (IPC client)
│   └── script_wrapper.py                  # Generates the subprocess .py file from user script
├── settings/
│   └── index.html                          # Venv management page (Homey custom settings)
└── tests/
    ├── conftest.py                         # Shared fixtures: mock Homey SDK, tmp dirs
    ├── test_venv_manager.py
    ├── test_sandbox.py
    ├── test_homey_context.py
    ├── test_script_wrapper.py
    ├── test_homey_bridge.py        # HomeyBridge IPC tested implicitly via test_runner.py (real subprocess)
    ├── test_runner.py
    └── test_executor.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `app.json`
- Create: `app.py`
- Create: `pythonscript/__init__.py`
- Create: `pyproject.toml`

- [ ] **Step 1: Write `app.json`**

```json
{
  "id": "nl.hoeve.pythonscript",
  "version": "1.0.0",
  "compatibility": ">=12.0.0",
  "runtime": "python",
  "pythonVersion": "3.14",
  "sdk": 3,
  "name": { "en": "Python Script", "nl": "Python Script" },
  "description": { "en": "Run Python code from Advanced Flows", "nl": "Voer Python-code uit vanuit Advanced Flows" },
  "category": ["tools"],
  "platforms": ["local"],
  "images": {
    "small": "/assets/images/small.png",
    "large": "/assets/images/large.png",
    "xlarge": "/assets/images/xlarge.png"
  },
  "author": { "name": "Jacco Hoeve" },
  "pythonDependencies": ["restrictedpython>=7.0.0"]
}
```

- [ ] **Step 2: Write `app.py` skeleton**

```python
from homey import app


class PythonScriptApp(app.App):
    async def on_init(self) -> None:
        self.log("PythonScriptApp initialised")


homey_export = PythonScriptApp
```

- [ ] **Step 3: Write `pythonscript/__init__.py`** (empty)

```python
```

- [ ] **Step 4: Write `pyproject.toml`**

```toml
[project]
name = "homey-pythonscript"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = ["restrictedpython>=7.0.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 5: Create placeholder assets** (empty PNGs are fine for development)

```bash
mkdir -p assets/images
touch assets/images/small.png assets/images/large.png assets/images/xlarge.png
```

- [ ] **Step 6: Commit**

```bash
git add app.json app.py pythonscript/__init__.py pyproject.toml assets/
git commit -m "chore: project scaffold"
```

---

## Task 2: Flow Card Manifests

**Files:**
- Create: `.homeycompose/flow/actions/run_script.json`
- Create: `.homeycompose/flow/actions/run_script_with_argument.json`

- [ ] **Step 1: Create directory**

```bash
mkdir -p .homeycompose/flow/actions
```

- [ ] **Step 2: Write `run_script.json`**

```json
{
  "title": { "en": "Run Script", "nl": "Script uitvoeren" },
  "titleFormatted": { "en": "Run [[script]]", "nl": "Voer [[script]] uit" },
  "highlight": true,
  "args": [
    {
      "name": "script",
      "type": "textarea",
      "title": { "en": "Script", "nl": "Script" },
      "placeholder": { "en": "homey.set_tag('result', 42)\nreturn 'done'" }
    },
    {
      "name": "requirements",
      "type": "textarea",
      "title": { "en": "Requirements (pip format)", "nl": "Requirements (pip-formaat)" },
      "placeholder": { "en": "requests==2.31.0\nnumpy>=1.26.0" }
    },
    {
      "name": "sandbox",
      "type": "checkbox",
      "title": { "en": "Sandboxed (RestrictedPython)", "nl": "Sandbox (RestrictedPython)" },
      "default": true
    },
    {
      "name": "timeout",
      "type": "number",
      "title": { "en": "Timeout (seconds)", "nl": "Time-out (seconden)" },
      "placeholder": { "en": "30" },
      "min": 1,
      "max": 300
    }
  ],
  "tokens": [
    { "name": "return_value", "type": "string", "title": { "en": "Return value", "nl": "Returnwaarde" }, "example": "42" },
    { "name": "error", "type": "string", "title": { "en": "Error", "nl": "Fout" }, "example": "ValueError: ..." }
  ]
}
```

- [ ] **Step 3: Write `run_script_with_argument.json`**

Copy `run_script.json` and add an `argument` arg before `script`:

```json
{
  "title": { "en": "Run Script with Argument", "nl": "Script uitvoeren met argument" },
  "titleFormatted": { "en": "Run [[script]] with [[argument]]", "nl": "Voer [[script]] uit met [[argument]]" },
  "highlight": true,
  "args": [
    {
      "name": "argument",
      "type": "text",
      "title": { "en": "Argument", "nl": "Argument" },
      "placeholder": { "en": "Value passed as `args` in script" }
    },
    {
      "name": "script",
      "type": "textarea",
      "title": { "en": "Script", "nl": "Script" },
      "placeholder": { "en": "# args contains the argument\nreturn args.upper()" }
    },
    {
      "name": "requirements",
      "type": "textarea",
      "title": { "en": "Requirements (pip format)", "nl": "Requirements (pip-formaat)" },
      "placeholder": { "en": "requests==2.31.0" }
    },
    {
      "name": "sandbox",
      "type": "checkbox",
      "title": { "en": "Sandboxed (RestrictedPython)", "nl": "Sandbox (RestrictedPython)" },
      "default": true
    },
    {
      "name": "timeout",
      "type": "number",
      "title": { "en": "Timeout (seconds)", "nl": "Time-out (seconden)" },
      "placeholder": { "en": "30" },
      "min": 1,
      "max": 300
    }
  ],
  "tokens": [
    { "name": "return_value", "type": "string", "title": { "en": "Return value", "nl": "Returnwaarde" }, "example": "42" },
    { "name": "error", "type": "string", "title": { "en": "Error", "nl": "Fout" }, "example": "ValueError: ..." }
  ]
}
```

- [ ] **Step 4: Commit**

```bash
git add .homeycompose/
git commit -m "feat: flow card manifests for Run Script and Run Script with Argument"
```

---

## Task 3: VenvManager

**Files:**
- Create: `pythonscript/venv_manager.py`
- Create: `tests/conftest.py`
- Create: `tests/test_venv_manager.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
import pytest
from pathlib import Path


@pytest.fixture
def tmp_venv_dir(tmp_path):
    """Temporary directory for venv storage."""
    venv_root = tmp_path / "venvs"
    venv_root.mkdir()
    return venv_root
```

- [ ] **Step 2: Write failing tests in `tests/test_venv_manager.py`**

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_venv_manager.py -v
```

Expected: `ModuleNotFoundError: No module named 'pythonscript.venv_manager'`

- [ ] **Step 4: Write `pythonscript/venv_manager.py`**

```python
import hashlib
import json
import shutil
import sys
import subprocess
from pathlib import Path


class VenvManager:
    def __init__(self, venv_root: Path):
        self._root = Path(venv_root)

    def _hash(self, requirements: str) -> str:
        normalised = requirements.strip()
        return hashlib.sha256(normalised.encode()).hexdigest()

    def _hash_file(self, card_uid: str) -> Path:
        return self._root / card_uid / ".requirements_hash"

    def _write_hash(self, card_uid: str, requirements: str) -> None:
        (self._root / card_uid).mkdir(parents=True, exist_ok=True)
        self._hash_file(card_uid).write_text(self._hash(requirements))

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
        entries = []
        for d in self._root.iterdir():
            if not d.is_dir():
                continue
            hf = d / ".requirements_hash"
            entries.append({
                "card_uid": d.name,
                "hash": hf.read_text() if hf.exists() else None,
            })
        return entries

    def venv_path(self, card_uid: str) -> Path:
        return self._root / card_uid

    async def build(self, card_uid: str, requirements: str) -> None:
        """pip install requirements into venvs/{card_uid}/. Raises on failure."""
        venv_dir = self.venv_path(card_uid)
        venv_dir.mkdir(parents=True, exist_ok=True)

        # Create venv
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
        )

        # Install requirements
        pip = venv_dir / "bin" / "pip"
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(requirements.strip())
            req_file = f.name

        try:
            subprocess.run(
                [str(pip), "install", "-r", req_file],
                check=True,
                capture_output=True,
            )
        finally:
            Path(req_file).unlink(missing_ok=True)

        self._write_hash(card_uid, requirements)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_venv_manager.py -v
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add pythonscript/venv_manager.py tests/conftest.py tests/test_venv_manager.py
git commit -m "feat: VenvManager - hash check, build, delete, list"
```

---

## Task 4: RestrictedPython Sandbox

**Files:**
- Create: `pythonscript/sandbox.py`
- Create: `tests/test_sandbox.py`

The sandbox compiles user code with RestrictedPython, execs it in a restricted namespace,
and captures the return value. The `homey` object is injected but its behaviour is tested
separately (Task 6). Here we test the security enforcement only.

- [ ] **Step 1: Write failing tests in `tests/test_sandbox.py`**

```python
import pytest
from pythonscript.sandbox import Sandbox, SecurityError


class TestSandboxAllowed:
    @pytest.mark.asyncio
    async def test_return_value(self):
        sb = Sandbox()
        result = await sb.run("return 42")
        assert result["return_value"] == 42

    @pytest.mark.asyncio
    async def test_return_string(self):
        sb = Sandbox()
        result = await sb.run("return 'hello'")
        assert result["return_value"] == "hello"

    @pytest.mark.asyncio
    async def test_arithmetic(self):
        sb = Sandbox()
        result = await sb.run("x = 2 + 2\nreturn x")
        assert result["return_value"] == 4

    @pytest.mark.asyncio
    async def test_no_return_gives_none(self):
        sb = Sandbox()
        result = await sb.run("x = 1")
        assert result["return_value"] is None

    @pytest.mark.asyncio
    async def test_math_module_allowed(self):
        sb = Sandbox()
        result = await sb.run("import math\nreturn math.sqrt(16)")
        assert result["return_value"] == 4.0

    @pytest.mark.asyncio
    async def test_set_tag_collected(self):
        sb = Sandbox()
        result = await sb.run("homey.set_tag('x', 99)", homey=_MockHomey())
        assert result["tags"]["x"] == 99


class TestSandboxBlocked:
    @pytest.mark.asyncio
    async def test_import_os_blocked(self):
        sb = Sandbox()
        with pytest.raises(SecurityError):
            await sb.run("import os")

    @pytest.mark.asyncio
    async def test_import_subprocess_blocked(self):
        sb = Sandbox()
        with pytest.raises(SecurityError):
            await sb.run("import subprocess")

    @pytest.mark.asyncio
    async def test_open_blocked(self):
        sb = Sandbox()
        with pytest.raises(SecurityError):
            await sb.run("open('/etc/passwd')")

    @pytest.mark.asyncio
    async def test_exec_blocked(self):
        sb = Sandbox()
        with pytest.raises(SecurityError):
            await sb.run("exec('import os')")

    @pytest.mark.asyncio
    async def test_dunder_access_blocked(self):
        sb = Sandbox()
        with pytest.raises(SecurityError):
            await sb.run("[].__class__.__bases__[0].__subclasses__()")


class TestSandboxErrors:
    @pytest.mark.asyncio
    async def test_syntax_error_propagates(self):
        sb = Sandbox()
        with pytest.raises(SyntaxError):
            await sb.run("def (")

    @pytest.mark.asyncio
    async def test_runtime_error_propagates(self):
        sb = Sandbox()
        with pytest.raises(ValueError):
            await sb.run("raise ValueError('bad')")

    @pytest.mark.asyncio
    async def test_args_injected(self):
        sb = Sandbox()
        result = await sb.run("return args", args="hello")
        assert result["return_value"] == "hello"


class _MockHomey:
    def __init__(self):
        self._tags = {}

    def set_tag(self, name, value):
        self._tags[name] = value
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_sandbox.py -v
```

Expected: `ModuleNotFoundError: No module named 'pythonscript.sandbox'`

- [ ] **Step 3: Write `pythonscript/sandbox.py`**

```python
import asyncio
import textwrap
from RestrictedPython import compile_restricted, safe_globals, safe_builtins
from RestrictedPython.Guards import safe_globals as rp_safe_globals, guarded_getattr, guarded_getitem


class SecurityError(Exception):
    pass


_ALLOWED_IMPORTS = frozenset({
    "math", "json", "datetime", "re", "collections", "itertools",
    "functools", "string", "decimal", "fractions", "statistics",
})


def _make_restricted_import(allowed: frozenset):
    def _import(name, *args, **kwargs):
        top = name.split(".")[0]
        if top not in allowed:
            raise SecurityError(f"import '{name}' is not allowed in sandboxed mode")
        return __builtins__["__import__"](name, *args, **kwargs)
    return _import


def _blocked_open(*args, **kwargs):
    raise SecurityError("open() is not allowed in sandboxed mode")


def _safe_write(obj):
    return obj


def _safe_getattr(obj, name, *args):
    if name.startswith("_"):
        raise SecurityError(f"access to '{name}' is not allowed")
    return getattr(obj, name, *args)


class Sandbox:
    async def run(
        self,
        script: str,
        homey=None,
        args: str | None = None,
    ) -> dict:
        """
        Compile and execute `script` under RestrictedPython.
        Returns {"return_value": ..., "tags": {...}}.
        Raises SecurityError, SyntaxError, or any exception the script raises.
        """
        wrapped = self._wrap(script, args)
        code = compile_restricted(wrapped, "<script>", "exec")

        builtins = dict(safe_builtins)
        builtins["__import__"] = _make_restricted_import(_ALLOWED_IMPORTS)
        builtins["open"] = _blocked_open

        namespace = {
            "__builtins__": builtins,
            "_getattr_": _safe_getattr,
            "_getitem_": guarded_getitem,
            "_getiter_": iter,
            "_write_": _safe_write,
            "homey": homey,
        }

        exec(code, namespace)  # defines _run in namespace
        result = await namespace["_run"]()
        tags = homey._tags if homey is not None else {}
        return {"return_value": result, "tags": dict(tags)}

    def _wrap(self, script: str, args) -> str:
        body = textwrap.indent(textwrap.dedent(script), "    ")
        args_repr = repr(args)
        return f"async def _run():\n    args = {args_repr}\n{body}\n"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_sandbox.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add pythonscript/sandbox.py tests/test_sandbox.py
git commit -m "feat: RestrictedPython sandbox with security enforcement"
```

---

## Task 5: HomeyContext (sandboxed homey object)

**Files:**
- Create: `pythonscript/homey_context.py`
- Create: `tests/test_homey_context.py`

`HomeyContext` is injected as `homey` in sandboxed mode. It holds a reference to
the Homey SDK's homey object and calls through to it. Tags are collected locally.

- [ ] **Step 1: Write failing tests in `tests/test_homey_context.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pythonscript.homey_context import HomeyContext


@pytest.fixture
def mock_sdk():
    """Mock Homey SDK homey object."""
    sdk = MagicMock()
    sdk.settings.get = MagicMock(return_value=None)
    sdk.settings.set = MagicMock()
    return sdk


class TestSetTag:
    def test_set_tag_stores_value(self, mock_sdk):
        ctx = HomeyContext(sdk=mock_sdk)
        ctx.set_tag("temp", 22.5)
        assert ctx._tags["temp"] == 22.5

    def test_set_tag_multiple(self, mock_sdk):
        ctx = HomeyContext(sdk=mock_sdk)
        ctx.set_tag("a", 1)
        ctx.set_tag("b", "hello")
        assert ctx._tags == {"a": 1, "b": "hello"}


class TestLogic:
    @pytest.mark.asyncio
    async def test_get_variable(self, mock_sdk):
        mock_sdk.logic.get_variables = AsyncMock(
            return_value=[{"name": "temperature", "value": 21.5}]
        )
        ctx = HomeyContext(sdk=mock_sdk)
        result = await ctx.logic.get_variable("temperature")
        assert result == 21.5

    @pytest.mark.asyncio
    async def test_get_variable_not_found_returns_none(self, mock_sdk):
        mock_sdk.logic.get_variables = AsyncMock(return_value=[])
        ctx = HomeyContext(sdk=mock_sdk)
        result = await ctx.logic.get_variable("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_variable(self, mock_sdk):
        mock_var = AsyncMock()
        mock_sdk.logic.get_variables = AsyncMock(
            return_value=[{"id": "var-1", "name": "temperature", "value": 21.5, "_obj": mock_var}]
        )
        ctx = HomeyContext(sdk=mock_sdk)
        await ctx.logic.set_variable("temperature", 25.0)
        mock_var.set_value.assert_called_once_with(25.0)


class TestDevices:
    @pytest.mark.asyncio
    async def test_get_capability(self, mock_sdk):
        mock_device = MagicMock()
        mock_device.capabilitiesObj = {"measure_temperature": MagicMock(value=21.5)}
        mock_sdk.devices.get_device = AsyncMock(return_value=mock_device)
        ctx = HomeyContext(sdk=mock_sdk)
        result = await ctx.devices.get_capability("device-1", "measure_temperature")
        assert result == 21.5

    @pytest.mark.asyncio
    async def test_set_capability(self, mock_sdk):
        mock_device = AsyncMock()
        mock_sdk.devices.get_device = AsyncMock(return_value=mock_device)
        ctx = HomeyContext(sdk=mock_sdk)
        await ctx.devices.set_capability("device-1", "onoff", True)
        mock_device.set_capability_value.assert_called_once_with("onoff", True)


class TestFlow:
    @pytest.mark.asyncio
    async def test_trigger(self, mock_sdk):
        mock_sdk.flow.run_flow_card_trigger = AsyncMock()
        ctx = HomeyContext(sdk=mock_sdk)
        await ctx.flow.trigger("flow-id-123")
        mock_sdk.flow.run_flow_card_trigger.assert_called_once()
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_homey_context.py -v
```

- [ ] **Step 3: Write `pythonscript/homey_context.py`**

```python
class HomeyContext:
    def __init__(self, sdk):
        self._sdk = sdk
        self._tags: dict = {}

    def set_tag(self, name: str, value) -> None:
        self._tags[name] = value

    @property
    def logic(self):
        return _LogicContext(self._sdk)

    @property
    def devices(self):
        return _DevicesContext(self._sdk)

    @property
    def flow(self):
        return _FlowContext(self._sdk)


class _LogicContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def get_variable(self, name: str):
        variables = await self._sdk.logic.get_variables()
        for v in variables:
            if v["name"] == name:
                return v["value"]
        return None

    async def set_variable(self, name: str, value) -> None:
        variables = await self._sdk.logic.get_variables()
        for v in variables:
            if v["name"] == name:
                await v["_obj"].set_value(value)
                return
        raise KeyError(f"Variable '{name}' not found")


class _DevicesContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def get_capability(self, device_id: str, capability: str):
        device = await self._sdk.devices.get_device(device_id)
        return device.capabilitiesObj[capability].value

    async def set_capability(self, device_id: str, capability: str, value) -> None:
        device = await self._sdk.devices.get_device(device_id)
        await device.set_capability_value(capability, value)


class _FlowContext:
    def __init__(self, sdk):
        self._sdk = sdk

    async def trigger(self, flow_id: str) -> None:
        await self._sdk.flow.run_flow_card_trigger(flow_id)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_homey_context.py -v
```

Expected: all green. Adjust SDK mock calls if the actual Python SDK uses different method names — verify against the installed SDK.

- [ ] **Step 5: Commit**

```bash
git add pythonscript/homey_context.py tests/test_homey_context.py
git commit -m "feat: HomeyContext - sandboxed homey object with devices, logic, flow"
```

---

## Task 6: Script Wrapper (subprocess)

**Files:**
- Create: `pythonscript/script_wrapper.py`
- Create: `tests/test_script_wrapper.py`

`script_wrapper.py` generates a complete Python script file that wraps the user's code
in an async runner with the HomeyBridge IPC client. This file is written to a tmp path
and executed as a subprocess.

- [ ] **Step 1: Write failing tests in `tests/test_script_wrapper.py`**

```python
import ast
import pytest
from pythonscript.script_wrapper import generate_wrapper


class TestGenerateWrapper:
    def test_output_is_valid_python(self):
        code = generate_wrapper("return 42", args=None)
        ast.parse(code)  # raises SyntaxError if invalid

    def test_user_script_embedded(self):
        code = generate_wrapper("x = 1\nreturn x", args=None)
        assert "x = 1" in code
        assert "return x" in code

    def test_args_injected_as_none(self):
        code = generate_wrapper("return args", args=None)
        assert "args = None" in code

    def test_args_injected_as_string(self):
        code = generate_wrapper("return args", args="hello world")
        assert repr("hello world") in code

    def test_contains_homey_bridge_import(self):
        code = generate_wrapper("return 1", args=None)
        assert "HomeyBridge" in code

    def test_contains_async_run_function(self):
        code = generate_wrapper("return 42", args=None)
        assert "async def _run" in code

    def test_return_value_sent_via_protocol(self):
        code = generate_wrapper("return 42", args=None)
        assert '"type": "return"' in code or "'type': 'return'" in code

    def test_exception_sent_via_protocol(self):
        code = generate_wrapper("return 42", args=None)
        assert '"type": "error"' in code or "'type': 'error'" in code
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_script_wrapper.py -v
```

- [ ] **Step 3: Write `pythonscript/script_wrapper.py`**

```python
import textwrap

_BRIDGE_SOURCE = '''
import sys as _sys
import json as _json
import asyncio as _asyncio

# Redirect user print() to stderr so stdout is protocol-only
_real_stdout = _sys.stdout
_sys.stdout = _sys.stderr


def _send(msg: dict) -> None:
    _real_stdout.write(_json.dumps(msg) + "\\n")
    _real_stdout.flush()


def _recv() -> dict:
    return _json.loads(_sys.stdin.readline())


class HomeyBridge:
    def __init__(self):
        self._tags: dict = {}

    def set_tag(self, name: str, value) -> None:
        _send({"type": "set_tag", "name": name, "value": value})

    @property
    def logic(self):
        return _LogicBridge(self)

    @property
    def devices(self):
        return _DevicesBridge(self)

    @property
    def flow(self):
        return _FlowBridge(self)

    def _rpc(self, method: str, args: list):
        _send({"type": "call", "method": method, "args": args})
        response = _recv()
        if "error" in response:
            raise RuntimeError(response["error"])
        return response["result"]

    async def _arpc(self, method: str, args: list):
        loop = _asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._rpc, method, args)


class _LogicBridge:
    def __init__(self, bridge):
        self._b = bridge

    async def get_variable(self, name: str):
        return await self._b._arpc("logic.get_variable", [name])

    async def set_variable(self, name: str, value) -> None:
        await self._b._arpc("logic.set_variable", [name, value])


class _DevicesBridge:
    def __init__(self, bridge):
        self._b = bridge

    async def get_capability(self, device_id: str, capability: str):
        return await self._b._arpc("devices.get_capability", [device_id, capability])

    async def set_capability(self, device_id: str, capability: str, value) -> None:
        await self._b._arpc("devices.set_capability", [device_id, capability, value])


class _FlowBridge:
    def __init__(self, bridge):
        self._b = bridge

    async def trigger(self, flow_id: str) -> None:
        await self._b._arpc("flow.trigger", [flow_id])


homey = HomeyBridge()
'''

_RUNNER_TEMPLATE = '''{bridge_source}

args = {args_repr}


async def _run():
{user_body}


async def _main():
    try:
        result = await _run()
        _send({{"type": "return", "value": result}})
    except Exception as _e:
        import traceback as _tb
        _send({{"type": "error", "message": str(_e), "traceback": _tb.format_exc()}})


_asyncio.run(_main())
'''


def generate_wrapper(script: str, args) -> str:
    user_body = textwrap.indent(textwrap.dedent(script), "    ")
    return _RUNNER_TEMPLATE.format(
        bridge_source=_BRIDGE_SOURCE,
        args_repr=repr(args),
        user_body=user_body,
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_script_wrapper.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pythonscript/script_wrapper.py tests/test_script_wrapper.py
git commit -m "feat: script wrapper generator for subprocess execution"
```

---

## Task 7: Full Python Runner

**Files:**
- Create: `pythonscript/runner.py`
- Create: `tests/test_runner.py`

`Runner` launches the generated wrapper as a subprocess, handles the JSON-lines IPC
protocol, dispatches Homey SDK calls back to the parent app, and returns the result dict.

- [ ] **Step 1: Write failing tests in `tests/test_runner.py`**

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from pythonscript.runner import Runner


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.logic.get_variables = AsyncMock(return_value=[{"name": "x", "value": 42}])
    sdk.devices.get_device = AsyncMock()
    return sdk


class TestRunnerBasic:
    @pytest.mark.asyncio
    async def test_return_value(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        result = await runner.run(script="return 42", args=None, timeout=10)
        assert result["return_value"] == 42

    @pytest.mark.asyncio
    async def test_return_string(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        result = await runner.run(script="return 'hello'", args=None, timeout=10)
        assert result["return_value"] == "hello"

    @pytest.mark.asyncio
    async def test_args_available(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        result = await runner.run(script="return args", args="test-value", timeout=10)
        assert result["return_value"] == "test-value"

    @pytest.mark.asyncio
    async def test_set_tag_collected(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        result = await runner.run(
            script="homey.set_tag('x', 99)\nreturn None",
            args=None,
            timeout=10,
        )
        assert result["tags"]["x"] == 99


class TestRunnerErrors:
    @pytest.mark.asyncio
    async def test_exception_propagates(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        with pytest.raises(RuntimeError, match="ZeroDivisionError"):
            await runner.run(script="return 1/0", args=None, timeout=10)

    @pytest.mark.asyncio
    async def test_timeout_raises(self, mock_sdk):
        runner = Runner(sdk=mock_sdk)
        with pytest.raises(TimeoutError):
            await runner.run(
                script="import time\ntime.sleep(60)",
                args=None,
                timeout=1,
            )


class TestRunnerVenv:
    @pytest.mark.asyncio
    async def test_venv_python_used_when_provided(self, mock_sdk, tmp_path):
        import sys
        runner = Runner(sdk=mock_sdk)
        result = await runner.run(
            script="import sys\nreturn sys.executable",
            args=None,
            timeout=10,
            venv_path=None,  # no venv, uses sys.executable
        )
        assert isinstance(result["return_value"], str)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_runner.py -v
```

- [ ] **Step 3: Write `pythonscript/runner.py`**

```python
import asyncio
import json
import sys
import tempfile
from pathlib import Path

from pythonscript.script_wrapper import generate_wrapper
from pythonscript.homey_context import HomeyContext


class Runner:
    def __init__(self, sdk):
        self._sdk = sdk

    async def run(
        self,
        script: str,
        args,
        timeout: int,
        venv_path: Path | None = None,
    ) -> dict:
        wrapper_code = generate_wrapper(script, args)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(wrapper_code)
            wrapper_file = f.name

        python = self._python_executable(venv_path)

        proc = await asyncio.create_subprocess_exec(
            python,
            wrapper_file,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        return_value = None
        tags: dict = {}
        error: str | None = None

        async def _pump():
            nonlocal return_value, error
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                msg = json.loads(line.decode())
                match msg["type"]:
                    case "set_tag":
                        tags[msg["name"]] = msg["value"]
                    case "return":
                        return_value = msg["value"]
                    case "error":
                        error = msg["message"]
                    case "call":
                        response = await self._dispatch(msg["method"], msg["args"])
                        proc.stdin.write(
                            (json.dumps({"result": response}) + "\n").encode()
                        )
                        await proc.stdin.drain()

        try:
            await asyncio.wait_for(
                asyncio.gather(_pump(), proc.wait()),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise TimeoutError(f"Script exceeded {timeout}s timeout")
        finally:
            Path(wrapper_file).unlink(missing_ok=True)

        if error:
            raise RuntimeError(error)

        return {"return_value": return_value, "tags": tags}

    def _python_executable(self, venv_path: Path | None) -> str:
        if venv_path is None:
            return sys.executable
        return str(venv_path / "bin" / "python")

    async def _dispatch(self, method: str, args: list):
        ctx = HomeyContext(sdk=self._sdk)
        match method:
            case "logic.get_variable":
                return await ctx.logic.get_variable(*args)
            case "logic.set_variable":
                await ctx.logic.set_variable(*args)
                return None
            case "devices.get_capability":
                return await ctx.devices.get_capability(*args)
            case "devices.set_capability":
                await ctx.devices.set_capability(*args)
                return None
            case "flow.trigger":
                await ctx.flow.trigger(*args)
                return None
            case _:
                raise ValueError(f"Unknown method: {method}")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_runner.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pythonscript/runner.py tests/test_runner.py
git commit -m "feat: full Python subprocess runner with JSON-lines IPC"
```

---

## Task 8: Executor

**Files:**
- Create: `pythonscript/executor.py`
- Create: `tests/test_executor.py`

`Executor` is the single entry point called by the card handlers. It decides whether to
use `Sandbox` or `Runner` based on the card arguments, and normalises the result into a
Homey token dict.

- [ ] **Step 1: Write failing tests in `tests/test_executor.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pythonscript.executor import Executor, ExecutionResult


@pytest.fixture
def mock_sdk():
    return MagicMock()


class TestExecutorRouting:
    @pytest.mark.asyncio
    async def test_sandboxed_flag_uses_sandbox(self, mock_sdk, tmp_path):
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Sandbox") as MockSandbox:
            instance = MockSandbox.return_value
            instance.run = AsyncMock(return_value={"return_value": 1, "tags": {}})
            result = await ex.run(
                script="return 1",
                args=None,
                sandbox=True,
                requirements="",
                timeout=30,
                card_uid="card-1",
            )
        MockSandbox.assert_called_once()
        assert result.return_value == 1

    @pytest.mark.asyncio
    async def test_no_sandbox_uses_runner(self, mock_sdk, tmp_path):
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner") as MockRunner:
            instance = MockRunner.return_value
            instance.run = AsyncMock(return_value={"return_value": 42, "tags": {"x": 1}})
            result = await ex.run(
                script="return 42",
                args=None,
                sandbox=False,
                requirements="",
                timeout=30,
                card_uid="card-1",
            )
        MockRunner.assert_called_once()
        assert result.return_value == 42
        assert result.tags["x"] == 1

    @pytest.mark.asyncio
    async def test_requirements_forces_runner(self, mock_sdk, tmp_path):
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Runner") as MockRunner:
            instance = MockRunner.return_value
            instance.run = AsyncMock(return_value={"return_value": None, "tags": {}})
            await ex.run(
                script="return 1",
                args=None,
                sandbox=True,  # sandbox=True is overridden by requirements
                requirements="requests==2.31.0",
                timeout=30,
                card_uid="card-1",
            )
        MockRunner.assert_called_once()

    @pytest.mark.asyncio
    async def test_return_value_stringified_for_homey(self, mock_sdk, tmp_path):
        ex = Executor(sdk=mock_sdk, venv_root=tmp_path)
        with patch("pythonscript.executor.Sandbox") as MockSandbox:
            instance = MockSandbox.return_value
            instance.run = AsyncMock(return_value={"return_value": 3.14, "tags": {}})
            result = await ex.run(
                script="return 3.14",
                args=None,
                sandbox=True,
                requirements="",
                timeout=30,
                card_uid="card-1",
            )
        assert result.homey_tokens["return_value"] == "3.14"
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_executor.py -v
```

- [ ] **Step 3: Write `pythonscript/executor.py`**

```python
from dataclasses import dataclass, field
from pathlib import Path

from pythonscript.sandbox import Sandbox
from pythonscript.runner import Runner
from pythonscript.venv_manager import VenvManager


@dataclass
class ExecutionResult:
    return_value: object
    tags: dict = field(default_factory=dict)

    @property
    def homey_tokens(self) -> dict:
        tokens = {"return_value": str(self.return_value) if self.return_value is not None else ""}
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

        if has_requirements or not sandbox:
            venv_path = self._vm.venv_path(card_uid) if has_requirements else None
            runner = Runner(sdk=self._sdk)
            raw = await runner.run(
                script=script,
                args=args,
                timeout=timeout,
                venv_path=venv_path,
            )
        else:
            from pythonscript.homey_context import HomeyContext
            homey_ctx = HomeyContext(sdk=self._sdk)
            sb = Sandbox()
            raw = await sb.run(script=script, homey=homey_ctx, args=args)

        return ExecutionResult(
            return_value=raw["return_value"],
            tags=raw.get("tags", {}),
        )
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/ -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add pythonscript/executor.py tests/test_executor.py
git commit -m "feat: Executor - routes sandbox vs subprocess, normalises result"
```

---

## Task 9: App Wiring

**Files:**
- Modify: `app.py`

Wire the card handlers in `on_init`, trigger venv pre-bake when a card argument
containing `requirements` is saved, and propagate errors to Homey's error path.

- [ ] **Step 1: Read `app.py` (current state)**

```python
# Current content:
from homey import app

class PythonScriptApp(app.App):
    async def on_init(self) -> None:
        self.log("PythonScriptApp initialised")

homey_export = PythonScriptApp
```

- [ ] **Step 2: Write updated `app.py`**

```python
import os
from pathlib import Path

from homey import app as homey_app

from pythonscript.executor import Executor
from pythonscript.venv_manager import VenvManager

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

    async def _on_run_script(self, card_arguments, **_) -> dict:
        return await self._execute(card_arguments, args=None)

    async def _on_run_script_with_argument(self, card_arguments, **_) -> dict:
        return await self._execute(card_arguments, args=card_arguments.get("argument"))

    async def _execute(self, card_arguments: dict, args) -> dict:
        script = card_arguments.get("script", "")
        requirements = card_arguments.get("requirements", "")
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
```

Note: `card_arguments.get("_uid")` — verify the exact key name Homey uses to pass the
card's unique ID; adjust if needed after testing against a real Homey SDK instance.

Error handling: exceptions raised from `_execute` propagate out of the `register_run_listener`
handler. The Homey SDK routes these to the card's error connection point automatically.
No try/except needed in the app — letting exceptions propagate IS the error-path wiring.

- [ ] **Step 3: Run all tests to confirm nothing broke**

```bash
pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: wire card handlers and executor in App.on_init"
```

---

## Task 10: Venv Pre-bake on Card Save

The current wiring builds the venv at run time (if needed). For the pre-bake UX — "env
ready the moment you save the card" — we register a listener on the flow card's
`register_argument_autocomplete_listener` or the equivalent save-time hook.

> **Note:** Verify in the Homey Python SDK whether action cards have a save/update hook.
> If not, keep the lazy rebuild at run time (Task 9 already does this). This task is a
> best-effort enhancement; the app is fully functional without it.

- [ ] **Step 1: Search SDK for card-save hooks**

```bash
python3 -c "import homey; help(homey.flow)" 2>/dev/null || echo "check SDK docs"
```

If a save hook exists, add it to `app.py`:

```python
run_card.register_argument_change_listener(
    "requirements",
    self._on_requirements_changed,
)

async def _on_requirements_changed(self, card_arguments, **_) -> None:
    requirements = card_arguments.get("requirements", "")
    card_uid = card_arguments.get("_uid", "default")
    if requirements and self._vm.needs_rebuild(card_uid, requirements):
        self.log(f"Pre-baking venv for card {card_uid}")
        await self._vm.build(card_uid, requirements)
        self.homey.settings.set(f"venv_status_{card_uid}", "ready")
```

- [ ] **Step 2: Commit if hook was found**

```bash
git add app.py
git commit -m "feat: pre-bake venv when requirements change at card-save time"
```

---

## Task 11: Settings Page (Venv Management)

**Files:**
- Create: `settings/index.html`
- Modify: `app.py` (register API endpoints)

Homey loads `settings/index.html` in an iframe inside the app's settings panel.
The page uses the Homey client SDK (loaded from CDN) to call the app's API.

- [ ] **Step 1: Register API endpoints in `app.py`**

Add to `on_init`:

```python
# Check SDK docs for the correct way to register settings API in Python.
# In the JS SDK: this.homey.api.registerGetHandler('/venvs', handler)
# Python equivalent (verify):
self.homey.api.register_handler("GET", "/venvs", self._api_list_venvs)
self.homey.api.register_handler("DELETE", "/venvs/:uid", self._api_delete_venv)

async def _api_list_venvs(self, params):
    return self._vm.list_venvs()

async def _api_delete_venv(self, params):
    uid = params.get("uid")
    self._vm.delete(uid)
    return {"ok": True}
```

- [ ] **Step 2: Write `settings/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Python Script Settings</title>
  <script src="https://cdn.jsdelivr.net/npm/homey-api@3/dist/HomeyAPI.min.js"></script>
  <style>
    body { font-family: sans-serif; padding: 16px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
    button { cursor: pointer; color: red; background: none; border: none; font-size: 14px; }
    #status { color: grey; font-size: 12px; margin-top: 8px; }
  </style>
</head>
<body>
  <h2>Python venv environments</h2>
  <p id="status">Loading...</p>
  <table>
    <thead><tr><th>Card UID</th><th>Hash</th><th></th></tr></thead>
    <tbody id="venv-list"></tbody>
  </table>

  <script>
    const homey = new Homey.HomeyAPI();

    async function load() {
      const venvs = await homey.api("GET", "/venvs");
      const tbody = document.getElementById("venv-list");
      tbody.innerHTML = "";
      if (!venvs.length) {
        document.getElementById("status").textContent = "No venv environments.";
        return;
      }
      document.getElementById("status").textContent = `${venvs.length} environment(s)`;
      for (const v of venvs) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${v.card_uid}</td>
          <td>${v.hash ? v.hash.slice(0, 12) + "..." : "—"}</td>
          <td><button onclick="del('${v.card_uid}')">Delete</button></td>
        `;
        tbody.appendChild(tr);
      }
    }

    async function del(uid) {
      if (!confirm(`Delete venv for ${uid}?`)) return;
      await homey.api("DELETE", `/venvs/${uid}`);
      load();
    }

    load();
  </script>
</body>
</html>
```

- [ ] **Step 3: Run all tests**

```bash
pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add settings/index.html app.py
git commit -m "feat: settings page for venv management with delete"
```

---

## Task 12: End-to-End Smoke Test

Run the app locally against a real Homey (or the Homey CLI emulator) and verify the golden paths.

- [ ] **Step 1: Install the app**

```bash
homey app run
```

- [ ] **Step 2: Test Run Script card (sandboxed)**

In a test flow: add "Run Script", paste `return 2 + 2`, sandbox ON. Run flow.
Expected: `return_value` tag = `"4"`.

- [ ] **Step 3: Test Run Script card (full Python)**

Paste `import math\nreturn str(math.pi)`, sandbox OFF.
Expected: `return_value` tag = `"3.141592653589793"`.

- [ ] **Step 4: Test set_tag**

Paste:
```python
homey.set_tag("greeting", "hello")
return "done"
```
Expected: `greeting` tag available downstream, `return_value` = `"done"`.

- [ ] **Step 5: Test error path**

Paste `raise ValueError("oops")`. Expected: flow routes to error connection, no crash.

- [ ] **Step 6: Test Run Script with Argument**

Set argument = `"world"` in the card. Script: `return f"hello {args}"`.
Expected: `return_value` = `"hello world"`.

- [ ] **Step 7: Test requirements**

Paste `requests==2.28.0` in requirements, sandbox OFF. Script: `import requests\nreturn requests.__version__`.
Expected: `return_value` = `"2.28.0"`.

- [ ] **Step 8: Commit final smoke-test confirmation**

```bash
git commit --allow-empty -m "test: end-to-end smoke test passed"
```
