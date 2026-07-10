import ast
from pythonscript.script_wrapper import (
    generate_wrapper,
    generate_sandbox_wrapper,
    _BRIDGE_SOURCE,
    _SANDBOX_BRIDGE_SOURCE,
)


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

    def test_contains_homey_bridge(self):
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


class TestGenerateSandboxWrapper:
    def test_output_is_valid_python(self):
        code = generate_sandbox_wrapper("return 42", args=None)
        ast.parse(code)

    def test_contains_homey_bridge(self):
        code = generate_sandbox_wrapper("return 1", args=None)
        assert "HomeyBridge" in code

    def test_contains_restricted_python_import(self):
        code = generate_sandbox_wrapper("return 1", args=None)
        assert "RestrictedPython" in code
        assert "compile_restricted_function" in code

    def test_script_body_embedded(self):
        code = generate_sandbox_wrapper("x = 42\nreturn x", args=None)
        assert "x = 42" in code

    def test_args_embedded(self):
        code = generate_sandbox_wrapper("return args", args="hello")
        assert repr("hello") in code

    def test_args_none_embedded(self):
        code = generate_sandbox_wrapper("return args", args=None)
        assert "args = None" in code

    def test_contains_return_protocol(self):
        code = generate_sandbox_wrapper("return 1", args=None)
        assert '"type": "return"' in code or "'type': 'return'" in code

    def test_contains_error_protocol(self):
        code = generate_sandbox_wrapper("return 1", args=None)
        assert '"type": "error"' in code or "'type': 'error'" in code

    def test_no_async_run_function(self):
        """Sandbox wrapper is synchronous — no asyncio.run()."""
        code = generate_sandbox_wrapper("return 1", args=None)
        assert "asyncio.run(_main())" not in code

    # F2: sandbox wrapper must use _SANDBOX_BRIDGE_SOURCE, not _BRIDGE_SOURCE
    def test_sandbox_wrapper_raises_on_logic(self):
        """Sandbox wrapper must contain the 'not available in sandboxed mode' error string."""
        code = generate_sandbox_wrapper("return 1", args=None)
        assert "not available in sandboxed mode" in code

    def test_sandbox_wrapper_has_no_async_arpc(self):
        """Sandbox wrapper must not contain async _arpc — no coroutines allowed."""
        code = generate_sandbox_wrapper("return 1", args=None)
        assert "async def _arpc" not in code

    def test_sandbox_wrapper_uses_sandbox_bridge_source(self):
        """generate_sandbox_wrapper must embed _SANDBOX_BRIDGE_SOURCE content."""
        code = generate_sandbox_wrapper("return 1", args=None)
        # The minimal sandbox bridge defines logic as a property raising RuntimeError
        assert "homey.logic not available" in code or "not available in sandboxed mode" in code


class TestBridgeSourceProperties:
    """F4: _BRIDGE_SOURCE must be thread-safe; _SANDBOX_BRIDGE_SOURCE must not have _rpc."""

    def test_bridge_source_contains_threading_lock(self):
        """Non-sandbox bridge must use a threading.Lock to protect _rpc send+recv."""
        assert "Lock" in _BRIDGE_SOURCE or "threading" in _BRIDGE_SOURCE

    def test_sandbox_bridge_source_has_no_rpc(self):
        """Sandbox bridge has no IPC at all — no _rpc, no race condition possible."""
        assert "_rpc" not in _SANDBOX_BRIDGE_SOURCE

    def test_sandbox_bridge_source_is_valid_python(self):
        """_SANDBOX_BRIDGE_SOURCE must be syntactically valid Python."""
        ast.parse(_SANDBOX_BRIDGE_SOURCE)

    def test_bridge_source_is_valid_python(self):
        """_BRIDGE_SOURCE must remain syntactically valid after adding the lock."""
        ast.parse(_BRIDGE_SOURCE)
