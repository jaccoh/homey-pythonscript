# Code Review Findings — fix/code-review-findings

## Status

| ID | Finding | Status | Notes |
|----|---------|--------|-------|
| F1 | Silent subprocess crash (no stderr, no returncode check) | DONE | runner.py — 6 new tests |
| F2 | Sandbox bridge: logic/devices/flow return unawaited coroutines | DONE | script_wrapper.py — _SANDBOX_BRIDGE_SOURCE, 6 new tests |
| F4 | `_rpc` not thread-safe (concurrent IPC races) | DONE | script_wrapper.py — threading.Lock, 4 new tests |
| F5 | `sandbox.py` dead code (entirely unused) | TODO | delete file |
| F6 | `HomeyContext.set_tag()` + `_tags` dead (never called in live path) | DONE | homey_context.py — removed, regression test added |
| F7 | `error` key in `homey_tokens` has no flow card token declaration | TODO | .homeycompose + app.json |
| F8 | `homey.set_tag()` invisible to flow editor (undocumented gap) | TODO | README |

## Details

### F1 — Silent subprocess crash
runner.py never reads proc.stderr or checks proc.returncode.
If wrapper module has a module-level SyntaxError (non-sandbox path), subprocess
exits non-zero, stdout is empty, pump gets EOF, runner returns {return_value: None}
with no error raised. User sees silent "success".

Fix: capture stderr alongside pump, after gather check returncode + raise if error is None.

### F2 — Sandbox bridge silent dead ends
Both sandbox and non-sandbox wrappers use the same _BRIDGE_SOURCE with _LogicBridge,
_DevicesBridge, _FlowBridge whose methods are all `async def`.
In sandbox the compiled function is synchronous — no await possible.
Calling homey.logic.get_variable("x") returns a coroutine object silently.
homey.set_tag() is the only bridge method that actually works in sandbox.

Fix: create _SANDBOX_BRIDGE_SOURCE with minimal HomeyBridge: only set_tag works,
logic/devices/flow raise RuntimeError immediately.

### F4 — _rpc thread-safety
_rpc sends then recvs over shared stdin/stdout without a lock.
asyncio.gather with multiple bridge calls → two threads race → wrong responses.
Fix: threading.Lock at module level in _BRIDGE_SOURCE protecting send+recv pair.

### F5 — sandbox.py dead code
Entire Sandbox class unreferenced since subprocess fix. Delete file.
test_sandbox.py tests the class directly — keep tests, add deprecation note.

### F6 — HomeyContext.set_tag dead
HomeyContext.set_tag() and _tags never used in live path.
Pump handles set_tag messages directly in runner.py:60. 
Only was used by now-deleted Sandbox class.
Fix: remove set_tag() and _tags from HomeyContext; update tests.

### F7 — error token undeclared
homey_tokens always returns {"error": ""} but no flow card defines error token.
Homey silently ignores undeclared keys. Either declare token in all cards or remove.
Fix: declare error token in all three action cards.

### F8 — set_tag invisible in flow editor
Custom tags from homey.set_tag() are merged into homey_tokens but flow cards
only declare return_value. Tags work for exec_script API but not in flow editor.
Fix: document clearly in README.
