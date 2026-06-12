# homey-pythonscript — Design Spec

Date: 2026-06-12

## What This Is

A Homey app (Python SDK) that lets users run Python code directly from Homey Advanced Flows — the Python equivalent of HomeyScript (which is JavaScript-only). Users write Python scripts in the flow card editor, with full access to the Homey API, and get results back as flow tags.

Target platforms: Homey Self-Hosted Server (primary), Homey Pro 2023/2026, Homey Pro mini.

---

## Cards

Two action cards — identical UX, only difference is whether the card receives an argument from the flow:

| Card | Flow input | Script variable |
|---|---|---|
| **Run Script** | — | — |
| **Run Script with Argument** | string from flow | `args` |

### Card Editor UI

Both cards share the same configuration screen, organized in two tabs:

**Tab: Script**
- Large multi-line code editor
- Play button — runs the script immediately, shows stdout + return value + errors in an output pane below the editor
- Sandbox toggle — sandboxed (default) or full Python
- Timeout field — integer, seconds, default 30

**Tab: Requirements**
- Multi-line text field (pip requirements.txt format)
- Venv status indicator: idle / building / ready / error
- Filling in requirements automatically implies full Python (sandbox toggle overridden)

### Card Outputs

Every card has two connection points:
- **Right** — success path; output tags available to downstream cards
- **Bottom** — error path; Homey routes here on exception; error message available as a tag

Output tags are populated via:
- `return value` — primary output tag (number, string, or boolean)
- `homey.set_tag("name", value)` — named output tags, any number of them

Both mechanisms work in both cards.

---

## The `homey` Object

Injected into every script execution. API mirrors HomeyScript:

```python
# Logic variables
val = await homey.logic.get_variable("name")
await homey.logic.set_variable("name", 42)

# Devices
temp = await homey.devices.get_capability("device-id", "measure_temperature")
await homey.devices.set_capability("device-id", "onoff", True)

# Trigger a flow
await homey.flow.trigger("flow-id")

# Set named output tags
homey.set_tag("temperature_f", val * 1.8 + 32)

# Argument (Run Script with Argument only)
print(args)  # string passed in from the flow
```

Scripts run in an async context — `await` works at the top level.

---

## Execution Tiers

| Tier | How to activate | What is allowed |
|---|---|---|
| **Sandboxed** | Default | RestrictedPython — curated stdlib subset, no filesystem, no network, no arbitrary imports |
| **Full Python** | Sandbox toggle off | Full stdlib, network, filesystem (container scope) |
| **Requirements** | Any text in requirements tab | Full Python + user packages, venv pre-baked at card save time |

Requirements automatically implies full Python. The sandbox toggle is disabled when requirements are present.

A sandboxed script that attempts a forbidden operation raises `SecurityError: not allowed` — this flows to the error path.

---

## Execution Architecture

### At card save time

1. Requirements field is hashed (SHA-256 of the text)
2. If hash differs from last known hash for this card: rebuild venv
   - `pip install -r <tmpfile>` into `venvs/{card_uid}/`
   - Store new hash alongside the venv
3. If requirements are empty and a venv exists: leave it (may be from a prior version)

### At card run time

1. Write script to `tmp/{card_id}.py` (or in-memory for sandboxed)
2. **Sandboxed**: compile with RestrictedPython, exec in restricted namespace with `homey` injected
3. **Full Python**: launch subprocess, activate `venvs/{card_uid}/` if present, set timeout
4. Collect return value and all `set_tag()` calls
5. On success: return tags to Homey, trigger right connection
6. On exception or timeout: raise error to Homey, trigger bottom connection

### Script wrapper (full Python)

The user's script is the literal body of an async function — no code transformation needed. `return` works naturally:

```python
import asyncio
from homey_bridge import HomeyBridge

homey = HomeyBridge()  # communicates back to the app over IPC

async def _run():
    args = "<injected from card>"
    # --- user script begins here ---
    temp = await homey.devices.get_capability("sensor-id", "measure_temperature")
    return temp * 1.8 + 32
    # --- user script ends here ---

result = asyncio.run(_run())
# result is sent back to the app over IPC
```

The runner captures the return value and all `set_tag()` calls and sends them back over IPC.

---

## Venv Management (App Settings)

A settings page lists all venvs:

| Card name | Packages | Built at | Actions |
|---|---|---|---|
| Sun position script | numpy 1.26, requests 2.31 | 2026-06-12 14:22 | Delete |
| Weather fetch | requests 2.31 | 2026-06-11 09:10 | Delete |

**Delete** removes the venv directory. The next card save rebuilds it. Use this when a requirements update did not install cleanly.

---

## Error Handling

- Script raises any exception → app catches, passes message + traceback to Homey error output
- Timeout exceeded → `TimeoutError` treated as any other exception
- pip install fails at card save → venv status shows "error" in the Requirements tab, card still saves (runs without that venv, may fail at runtime)
- Sandboxed violation → `SecurityError` raised, same error path

---

## Script Storage

- **Script text**: stored as a card argument by Homey (part of the flow definition — Homey manages backup and sync automatically)
- **Venvs**: stored on container filesystem at `venvs/{card_uid}/`, where `card_uid` is the Homey-assigned action instance UID; managed by the app
- **Requirements hash**: stored alongside each venv for change detection
- **Tmp files**: written at run time, cleaned up after execution

---

## Testing Strategy

- TDD throughout: write tests before implementation
- Unit tests for: RestrictedPython sandbox enforcement, script wrapper/IPC, venv hash comparison logic, HomeyBridge API methods
- Integration tests using mocked HomeyBridge and mocked Homey SDK
- Manual test via play button in card editor for golden path and error cases
