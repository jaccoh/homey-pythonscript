import asyncio
import json
import sys
import tempfile
from pathlib import Path

from pythonscript.script_wrapper import generate_wrapper, generate_sandbox_wrapper
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
        sandboxed: bool = False,
    ) -> dict:
        wrapper_code = generate_sandbox_wrapper(script, args) if sandboxed else generate_wrapper(script, args)

        wrapper_file = None
        proc = None
        return_value = None
        tags: dict = {}
        error: str | None = None
        stderr_text: str = ""

        try:
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

            async def _pump():
                nonlocal return_value, error
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    try:
                        msg = json.loads(line.decode())
                    except json.JSONDecodeError:
                        continue  # skip malformed lines, don't kill the subprocess
                    try:
                        match msg.get("type"):
                            case "set_tag":
                                tags[msg.get("name", "")] = msg.get("value")
                            case "return":
                                return_value = msg.get("value")
                            case "error":
                                tb = msg.get("traceback", "")
                                if tb:
                                    # last line of traceback: "ExceptionType: message"
                                    error = tb.strip().split("\n")[-1]
                                else:
                                    error = msg.get("message", "Unknown error")
                            case "call":
                                try:
                                    response = await self._dispatch(msg.get("method", ""), msg.get("args", []))
                                    reply = json.dumps({"result": response}) + "\n"
                                except Exception as e:
                                    reply = json.dumps({"error": str(e)}) + "\n"
                                try:
                                    proc.stdin.write(reply.encode())
                                    await proc.stdin.drain()
                                except (BrokenPipeError, ConnectionResetError, OSError):
                                    break
                    except Exception:
                        continue  # skip malformed messages

            async def _drain_stderr():
                nonlocal stderr_text
                data = await proc.stderr.read()
                stderr_text = data.decode(errors="replace")

            await asyncio.wait_for(
                asyncio.gather(_pump(), _drain_stderr(), proc.wait()),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Script exceeded {timeout}s timeout")
        finally:
            if proc is not None and proc.returncode is None:
                proc.kill()
                await proc.wait()
            if wrapper_file:
                Path(wrapper_file).unlink(missing_ok=True)

        if error:
            raise RuntimeError(error)

        if proc is not None and proc.returncode != 0:
            tail = stderr_text.strip()[-500:]
            raise RuntimeError(
                f"Script process exited with code {proc.returncode}\n{tail}"
            )

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
                tag = args[0] if args else ""
                await ctx.flow.trigger(tag)
                return None
            case _:
                raise ValueError(f"Unknown method: {method}")
