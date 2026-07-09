"""Device capability integration tests.

Requires HOMEY_TEST_DEVICE_ID env var — UUID of a device with onoff capability.
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_device(test_device_id):
    if not test_device_id:
        pytest.skip("HOMEY_TEST_DEVICE_ID not set")


class TestGetCapability:
    def test_onoff_returns_bool_string(self, shs, test_device_id):
        r = shs.exec(
            f'result = await homey.devices.get_capability("{test_device_id}", "onoff")\n'
            "return str(result)"
        )
        assert r["return_value"] in ("True", "False")

    def test_unknown_capability_returns_none(self, shs, test_device_id):
        r = shs.exec(
            f'result = await homey.devices.get_capability("{test_device_id}", "nonexistent_cap_xyz")\n'
            "return str(result)"
        )
        assert r["return_value"] == "None"


class TestSetCapability:
    def test_set_onoff_false_then_true(self, shs, test_device_id):
        shs.exec(
            f'await homey.devices.set_capability("{test_device_id}", "onoff", False)'
        )
        r = shs.exec(
            f'result = await homey.devices.get_capability("{test_device_id}", "onoff")\n'
            "return str(result)"
        )
        assert r["return_value"] == "False"

        shs.exec(
            f'await homey.devices.set_capability("{test_device_id}", "onoff", True)'
        )
        r = shs.exec(
            f'result = await homey.devices.get_capability("{test_device_id}", "onoff")\n'
            "return str(result)"
        )
        assert r["return_value"] == "True"
