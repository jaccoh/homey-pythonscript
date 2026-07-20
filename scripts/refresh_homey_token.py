"""Refresh the Athom OAuth access token used by the Homey CLI before deploy.

The Athom access token expires after ~1 hour. CI restores ~/.athom-cli/settings.json
from a secret that may be older than that, so this exchanges the stored refresh_token
for a fresh access_token before `homey app validate` / `homey app install` run.

ATHOM_API_CLIENT_ID / ATHOM_API_CLIENT_SECRET below are the Homey CLI's own OAuth
client credentials, public in the `homey` npm package (config.js). They identify the
CLI application, not a user — see https://www.npmjs.com/package/homey.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ATHOM_API_CLIENT_ID = "64691b4358336640a5ecee5c"
ATHOM_API_CLIENT_SECRET = "ed09f559ae12b1522d00431f0bf7c5755603c41e"
ATHOM_API_TOKEN_URL = "https://api.athom.com/oauth2/token"

SETTINGS_PATH = Path(os.environ.get("HOMEY_HOME", str(Path.home() / ".athom-cli"))) / "settings.json"


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    import base64

    return "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()


def main() -> None:
    settings = json.loads(SETTINGS_PATH.read_text())
    token = settings["homeyApi"]["token"]
    refresh_token = token["refresh_token"]

    body = urllib.parse.urlencode(
        {"grant_type": "refresh_token", "refresh_token": refresh_token}
    ).encode()
    req = urllib.request.Request(
        ATHOM_API_TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": _basic_auth_header(ATHOM_API_CLIENT_ID, ATHOM_API_CLIENT_SECRET),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            response = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise RuntimeError(f"Token refresh failed: HTTP {e.code}: {detail}") from None

    token["access_token"] = response["access_token"]
    token["refresh_token"] = response["refresh_token"]
    token["expires_in"] = response["expires_in"]
    token["token_type"] = response["token_type"]

    SETTINGS_PATH.write_text(json.dumps(settings, indent=4))
    print("Athom OAuth token refreshed.")


if __name__ == "__main__":
    main()
