"""
Integration test fixtures. Requires a running SHS with the app installed.

Auth priority:
  1. HOMEY_TOKEN env var
  2. ~/.athom-cli/settings.json homeyApi.token.access_token

URL: HOMEY_URL env var, default https://192-168-12-124.homey.homeylocal.com:4860

Device/logic config:
  HOMEY_TEST_DEVICE_ID  — UUID of a device with onoff capability
  HOMEY_TEST_LOGIC_VAR  — name of a logic variable to read-test
"""

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

import pytest

APP_ID = "nl.hoeve.pythonscript"
DEFAULT_URL = "https://192-168-12-124.homey.homeylocal.com:4860"


def _cli_token() -> str | None:
    path = Path.home() / ".athom-cli" / "settings.json"
    try:
        d = json.loads(path.read_text())
        return d.get("homeyApi", {}).get("token", {}).get("access_token")
    except Exception:
        return None


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: requires live SHS (run with -m integration)"
    )


@pytest.fixture(scope="session")
def homey_url() -> str:
    return os.environ.get("HOMEY_URL", DEFAULT_URL).rstrip("/")


@pytest.fixture(scope="session")
def homey_token() -> str:
    token = os.environ.get("HOMEY_TOKEN") or _cli_token()
    if not token:
        pytest.skip("No Homey token — set HOMEY_TOKEN or run homey login")
    return token


@pytest.fixture(scope="session")
def shs(homey_url, homey_token) -> "HomeyTestClient":
    return HomeyTestClient(homey_url, homey_token)


@pytest.fixture(scope="session")
def test_device_id() -> str | None:
    return os.environ.get("HOMEY_TEST_DEVICE_ID")


@pytest.fixture(scope="session")
def test_logic_var() -> str | None:
    return os.environ.get("HOMEY_TEST_LOGIC_VAR")


class HomeyTestClient:
    def __init__(self, base_url: str, token: str):
        self._base = base_url
        self._token = token
        self._ssl = ssl.create_default_context()
        self._ssl.check_hostname = False
        self._ssl.verify_mode = ssl.CERT_NONE

    def _req(self, method: str, path: str, body=None):
        url = f"{self._base}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method.upper(),
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
        )
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=self._ssl)
        )
        try:
            with opener.open(req) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:400]
            raise RuntimeError(f"HTTP {e.code} {method} {path}: {detail}") from None

    def app_info(self) -> dict:
        return self._req("GET", f"/api/app/{APP_ID}")

    def exec(self, script: str, args=None, timeout: int = 30) -> dict:
        return self._req(
            "POST",
            f"/api/app/{APP_ID}/exec",
            {"script": script, "args": args, "timeout": timeout},
        )
