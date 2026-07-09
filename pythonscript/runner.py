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
                try:
                    msg = json.loads(line.decode())
                except json.JSONDecodeError:
                    continue  # skip malformed lines, don't kill the subprocess
                match msg["type"]:
                    case "set_tag":
                        tags[msg["name"]] = msg["value"]
                    case "return":
                        return_value = msg["value"]
                    case "error":
                        tb = msg.get("traceback", "")
                        if tb:
                            # last line of traceback: "ExceptionType: message"
                            error = tb.strip().split("\n")[-1]
                        else:
                            error = msg["message"]
                    case "call":
                        try:
                            response = await self._dispatch(msg["method"], msg["args"])
                            reply = json.dumps({"result": response}) + "\n"
                        except Exception as e:
                            reply = json.dumps({"error": str(e)}) + "\n"
                        proc.stdin.write(reply.encode())
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
            case "flow.trigger":
                tag = args[0] if args else ""
                tokens = args[1] if len(args) > 1 else {}
                await ctx.flow.trigger(tag, tokens)
                return None
            case _:
                raise ValueError(f"Unknown method: {method}")
