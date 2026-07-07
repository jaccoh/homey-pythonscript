Python Script lets you run Python code directly from Advanced Flows.

== Flow Cards ==

Run Script
Run any Python snippet inline. Optionally pass an argument and set a timeout. Runs in a secure sandbox (RestrictedPython) — no file system or network access.

Run Script with Packages
Like Run Script, but with access to PyPI packages. Specify a requirements.txt-style list and a named environment. The environment is built once and reused on subsequent runs.

Run Named Script
Store and manage scripts via the app's settings page. Each script can be configured to run sandboxed or in a named environment. Trigger by name from a flow, optionally with an argument.

== Return Values ==

All cards return a `return_value` token containing whatever value the script returns (string, number, or JSON).

== Requirements ==

- Homey Pro (Early 2023 or later)
- Python scripts run on-device; no cloud required
