import operator
import textwrap
from RestrictedPython import compile_restricted_function, safe_builtins
from RestrictedPython.Guards import safer_getattr, full_write_guard


class SecurityError(Exception):
    pass


_ALLOWED_IMPORTS = frozenset({
    "math", "json", "datetime", "re", "collections", "itertools",
    "functools", "string", "decimal", "fractions", "statistics",
})

_FUNC_NAME = "script"


def _make_restricted_import(allowed: frozenset):
    builtin_import = __import__

    def _import(name, *args, **kwargs):
        top = name.split(".")[0]
        if top not in allowed:
            raise SecurityError(f"import '{name}' is not allowed in sandboxed mode")
        return builtin_import(name, *args, **kwargs)
    return _import


def _blocked_open(*args, **kwargs):
    raise SecurityError("open() is not allowed in sandboxed mode")


def _blocked_exec(*args, **kwargs):
    raise SecurityError("exec() is not allowed in sandboxed mode")


def _safe_getattr(obj, name, *args):
    """Block dunder/underscore attribute access; delegate the rest to safer_getattr."""
    if isinstance(name, str) and name.startswith("_"):
        raise SecurityError(f"access to '{name}' is not allowed in sandboxed mode")
    return safer_getattr(obj, name, *args) if args else safer_getattr(obj, name)


class Sandbox:
    async def run(
        self,
        script: str,
        homey=None,
        args=None,
    ) -> dict:
        # Prepend args injection into the script body
        body = f"args = {repr(args)}\n{textwrap.dedent(script)}"

        result = compile_restricted_function(
            p="homey",
            body=body,
            name=_FUNC_NAME,
            filename="<script>",
        )
        if result.errors:
            # Distinguish actual syntax errors from RestrictedPython security violations.
            # Syntax errors use the template: "Line N: SyntaxError: <msg> at statement: ..."
            # Security restrictions use: "Line N: <restriction message>"
            if any(": SyntaxError:" in e for e in result.errors):
                raise SyntaxError(result.errors)
            raise SecurityError("; ".join(result.errors))

        builtins = dict(safe_builtins)
        builtins["__import__"] = _make_restricted_import(_ALLOWED_IMPORTS)
        builtins["open"] = _blocked_open
        builtins["exec"] = _blocked_exec
        builtins["eval"] = _blocked_exec
        builtins["compile"] = _blocked_exec
        builtins["_getattr_"] = _safe_getattr

        namespace = {
            "__builtins__": builtins,
            "_getattr_": _safe_getattr,
            "_getitem_": operator.getitem,
            "_getiter_": iter,
            "_write_": full_write_guard,
        }

        exec(result.code, namespace)
        return_value = namespace[_FUNC_NAME](homey)
        tags = dict(homey._tags) if homey is not None else {}
        return {"return_value": return_value, "tags": tags}
