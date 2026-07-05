import ast
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
