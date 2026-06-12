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
