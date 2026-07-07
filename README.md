# Python Script

Automate your home with Python. Write Python scripts directly in Homey Advanced Flows — quick one-liners in a sandboxed card, or full programs with any pip package. A built-in IDE lets you save and manage named scripts without touching a flow card.

**Version:** 0.2.0 | **Requires:** Homey Pro (local) >= 13.0.0 | **Python:** 3.14

---

## Installation

Install from the [Homey App Store](https://homey.app/en-us/app/nl.hoeve.pythonscript/) or search for **Python Script** in the Homey app.

**Manual installation (while pending App Store approval)**

Requires [Node.js](https://nodejs.org/) and a Homey developer account.

```bash
git clone https://github.com/jaccoh/homey-pythonscript.git
cd homey-pythonscript
npm install -g homey
homey login
homey app install
```

The app installs directly on the Homey Pro selected during `homey login`.

---

## Features

- **Inline sandboxed scripts** — write Python directly in a flow card, no setup needed
- **Package support** — install any pip package into an isolated virtual environment, then use it from flows
- **Named scripts + IDE** — save scripts by name in the settings page (Monaco editor), select them by name in flows
- **Homey API access** — scripts can read/write logic variables, get/set device capabilities, and trigger flows
- **Tag output** — set flow tokens from your script using `homey.set_tag(name, value)`
- **Return values** — `return value` from a script becomes the `return_value` flow token

---

## Flow Cards

### Run Script
Write Python inline in the flow card. Runs in a RestrictedPython sandbox — no filesystem, no network, no subprocess. Fast and safe for simple logic.

```python
# Read a logic variable and return its value
value = await homey.logic.get_variable("temperature")
return value
```

| Field | Description |
|-------|-------------|
| Script | Python code |
| Argument (optional) | Passed as `args` inside the script |
| Timeout (optional) | Max execution time in seconds (default: 30) |

**Output token:** `return_value` (string)

---

### Run Script with Packages
Full Python in an isolated virtual environment. Packages install once and persist; rebuilt automatically when requirements change.

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
Run a script saved in the IDE. Sandbox mode and virtual environment are configured in the IDE — the flow card stays simple.

| Field | Description |
|-------|-------------|
| Script | Autocomplete from saved scripts |
| Argument (optional) | Passed as `args` |

**Output token:** `return_value` (string)

---

## Settings IDE

The settings page is a full Python IDE for managing scripts and virtual environments.

### Scripts tab

- Select a script from the dropdown or create a new one
- Edit code in the Monaco editor with Python syntax highlighting
- Toggle **Sandbox** mode — when disabled, select a virtual environment
- Run scripts directly from the IDE with live output
- Delete scripts with a two-click confirm

### Environments tab

- Create named virtual environments
- Edit pip requirements and click **Save & Build** to install
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

`args` is a string (or `None`) when an argument is passed from the flow card.

---

## FAQ

**Where do I see script output or errors?**
Run the script from the IDE settings page — output appears in the panel below the editor. In flows, errors appear as the `error` flow token on the card.

**Can the sandboxed card access the internet or files?**
No. The **Run Script** card uses RestrictedPython — no network, no filesystem, no subprocess. Use **Run Script with Packages** or a named script with sandbox disabled for full access.

**Can I install any pip package?**
Yes. Add packages to the Requirements field in pip format (`requests==2.31.0`, `numpy>=1.26.0`). They are installed into an isolated virtual environment on your Homey.

**My script times out — what do I do?**
The default timeout is 30 seconds. Increase it in the flow card (up to 300s), or optimise the script. Network calls and heavy computation are the common causes.

**Can scripts run in parallel?**
Each flow card execution is independent. Multiple flows triggering the same named script simultaneously will each run their own process.

---

## Development

**Requirements:** Python 3.14, [uv](https://github.com/astral-sh/uv)

```bash
# Install dependencies
uv sync

# Run tests
.venv/bin/pytest -v
```

> Use `.venv/bin/pytest` directly. `python -m pytest` and `uv run pytest` do not work in this project.

---

## Architecture

For contributors and developers:

```
app.py              — Homey app entry point, flow card listeners
api.py              — REST API endpoints called by the settings page
pythonscript/
  executor.py       — Routes to Sandbox or Runner based on config
  sandbox.py        — RestrictedPython execution
  runner.py         — Subprocess execution with optional venv
  venv_manager.py   — pip venv lifecycle (build, hash, list, delete)
  script_manager.py — Named script storage (.py + .json metadata)
  homey_context.py  — homey.* API surface for scripts
settings/
  index.html        — IDE (Monaco editor, Scripts + Environments tabs)
```

Named scripts are stored in `/userdata/scripts/` on the Homey. Virtual environments live in `/userdata/venvs/`.

---

## License

MIT — see [LICENSE](LICENSE) for details.

Author: [Jacco Hoeve](https://github.com/jaccoh)
