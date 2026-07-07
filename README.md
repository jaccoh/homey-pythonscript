# Python Script

Run Python code from Homey Advanced Flows. Write scripts inline in a flow card, or use the built-in IDE to save and manage named scripts with full package support.

**Version:** 0.2.0 | **Requires:** Homey Pro (local) >= 13.0.0 | **Python:** 3.14

---

## Features

- **Inline sandboxed scripts** — write Python directly in a flow card, no setup needed
- **Package support** — install any pip package into an isolated virtual environment, then use it from flow cards
- **Named scripts + IDE** — save scripts by name in the settings page (Monaco editor), select them by name in flows
- **Homey API access** — scripts can read/write logic variables, get/set device capabilities, and trigger flows
- **Tag output** — set flow tokens from your script using `homey.set_tag(name, value)`
- **Return values** — `return value` from a script becomes the `return_value` flow token

---

## Flow Cards

### Run Script
Write Python inline in the flow card. Runs in a RestrictedPython sandbox — no filesystem, no network, no subprocess. Fast and safe.

```python
# Get a logic variable and return it
value = await homey.logic.get_variable("temperature")
return value
```

| Field | Description |
|-------|-------------|
| Script | Python code |
| Argument (optional) | Passed as `args` inside the script |
| Timeout (optional) | Max execution time in seconds (default 30) |

**Output token:** `return_value` (string)

---

### Run Script with Packages
Full Python execution in an isolated virtual environment. Packages are installed once and reused. The environment is rebuilt automatically when requirements change.

```python
import requests
response = requests.get(f"https://api.example.com/temp?city={args}")
return response.json()["temperature"]
```

| Field | Description |
|-------|-------------|
| Script | Python code |
| Argument (optional) | Passed as `args` |
| Requirements | pip requirements (`requests==2.31.0`) |
| Environment name | Name for the virtual environment (autocomplete from existing) |
| Timeout (optional) | Max execution time in seconds |

**Output token:** `return_value` (string)

---

### Run Named Script
Run a script saved in the IDE. Sandbox mode and environment are configured in the IDE, not in the flow card — keeping the card simple.

| Field | Description |
|-------|-------------|
| Script | Autocomplete from saved scripts |
| Argument (optional) | Passed as `args` |

**Output token:** `return_value` (string)

---

## Settings IDE

The settings page is a full Python IDE for managing named scripts and virtual environments.

### Scripts tab

- Select a script from the dropdown or create a new one (name-only popup)
- Edit Python code in the Monaco editor with syntax highlighting
- Toggle **Sandbox** mode — when disabled, select a virtual environment to run the script in
- Run scripts directly from the IDE with live output
- Delete scripts with a two-click confirm

### Environments tab

- Create named virtual environments
- Edit pip requirements and rebuild with **Save & Build**
- Delete environments with a two-click confirm

---

## Homey API

Inside any script, `homey` is available:

```python
# Logic variables
value = await homey.logic.get_variable("my_var")
await homey.logic.set_variable("my_var", 42)

# Device capabilities
state = await homey.devices.get_capability(device_id, "onoff")
await homey.devices.set_capability(device_id, "dim", 0.5)

# Trigger a flow
await homey.flow.trigger("my_flow_id")

# Set a flow tag (token)
homey.set_tag("temperature", 21.5)

# Return a value to the flow
return "done"
```

`args` is available as a string (or `None`) when an argument is passed from the flow card.

---

## Architecture

```
app.py              — Homey app entry point, flow card listeners
api.py              — REST API endpoints for the settings page
pythonscript/
  executor.py       — Routes to Sandbox or Runner based on config
  sandbox.py        — RestrictedPython execution
  runner.py         — Subprocess-based execution with venv support
  venv_manager.py   — pip venv lifecycle (build, hash, list, delete)
  script_manager.py — Named script storage (code + metadata)
  homey_context.py  — homey.* API surface for scripts
settings/
  index.html        — IDE (Monaco editor, Scripts + Environments tabs)
```

Scripts are stored in `/userdata/scripts/{name}.py` with a companion `{name}.json` for metadata (sandbox flag, venv name). Virtual environments live in `/userdata/venvs/{name}/`.

---

## Development

**Requirements:** Python 3.14, uv

```bash
# Install dependencies
uv sync

# Run tests
.venv/bin/pytest -v
```

**Test runner note:** use `.venv/bin/pytest` directly — `python -m pytest` is blocked by a project hook.

---

## License

MIT — see [LICENSE](LICENSE) for details.

Author: Jacco Hoeve
