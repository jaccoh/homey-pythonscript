import ast
from pythonscript.script_wrapper import generate_wrapper, generate_sandbox_wrapper


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
