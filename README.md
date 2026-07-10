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
- **Homey API access** — scripts can set flow tags, trigger flows, and return values
- **Tag output** — `homey.set_tag(name, value)` stores key-value pairs in the exec_script API response and IDE run panel; not visible as tokens in the flow editor
- **Return values** — `return value` from a script becomes the `return_value` flow token; `error` is set automatically on failure

---

## Flow Cards

### Run Script
Write Python inline in the flow card. Runs in a RestrictedPython sandbox — no filesystem, no network, no subprocess. Fast and safe for simple logic.

```python
# Return a value to the flow
homey.set_tag("temperature", 21.5)  # stored in API response, not a flow token
return "done"
```

| Field | Description |
|-------|-------------|
| Script | Python code |
| Argument (optional) | Passed as `args` inside the script |
| Timeout (optional) | Max execution time in seconds (default: 30) |

**Output tokens:** `return_value` (string), `error` (string, empty on success)

> **Sandbox restrictions:** `homey.logic`, `homey.devices`, and `homey.flow` are not available in sandboxed scripts — calling them raises a `RuntimeError`. Only `homey.set_tag()` and `return` work.

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

**Output tokens:** `return_value` (string), `error` (string, empty on success)

---

### Run Named Script
Run a script saved in the IDE. Sandbox mode and virtual environment are configured in the IDE — the flow card stays simple.

| Field | Description |
|-------|-------------|
| Script | Autocomplete from saved scripts |
| Argument (optional) | Passed as `args` |

**Output tokens:** `return_value` (string), `error` (string, empty on success)

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
# Store a tag value (returned in exec_script API response and IDE run panel)
homey.set_tag("temperature", 21.5)

# Trigger a flow that has a "Flow triggered from Python" trigger card with matching tag
await homey.flow.trigger("my-tag")

# Read a logic variable (write is not supported — Homey restricts write access)
value = await homey.logic.get_variable("my_variable")

# Read or set a device capability
state = await homey.devices.get_capability("device-uuid", "onoff")
await homey.devices.set_capability("device-uuid", "onoff", False)

# Return a value to the flow
return "done"
```

`args` is a string (or `None`) when an argument is passed from the flow card.

> **`homey.set_tag(name, value)`** does **not** create a flow card token. Tag values are returned in the exec_script API response (`tags` key) and displayed in the IDE run panel. They are not visible in the Homey flow editor. Use `return value` to pass data to subsequent flow cards via the `return_value` token.

> **`homey.logic.set_variable()`** is not supported. Homey restricts logic variable write access to the HomeyScript app only. Use a Homey flow action to set variables instead.

> **`homey.flow.trigger(tag)`** fires all flows that have the "Flow triggered from Python" trigger card configured with the matching tag. Add that card to a flow in the Homey app first.

### Sandboxed vs non-sandboxed capabilities

| API | Sandboxed ("Run Script") | Non-sandboxed |
|-----|--------------------------|---------------|
| `return value` → `return_value` flow token | Yes | Yes |
| `homey.set_tag()` | Yes | Yes |
| `homey.logic.*` | No — raises `RuntimeError` | Yes |
| `homey.devices.*` | No — raises `RuntimeError` | Yes |
| `homey.flow.*` | No — raises `RuntimeError` | Yes |

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
