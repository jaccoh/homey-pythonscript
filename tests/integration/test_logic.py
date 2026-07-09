"""Logic variable integration tests.

Requires HOMEY_TEST_LOGIC_VAR env var — name of an existing logic variable.
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def require_logic_var(test_logic_var):
    if not test_logic_var:
        pytest.skip("HOMEY_TEST_LOGIC_VAR not set")


class TestGetVariable:
    def test_get_existing_variable(self, shs, test_logic_var):
        r = shs.exec(
            f'result = await homey.logic.get_variable("{test_logic_var}")\n'
            "return str(result)"
        )
        # Any non-error response is valid — variable type/value varies
        assert r["return_value"] != ""

    def test_get_missing_variable_returns_none(self, shs):
        r = shs.exec(
            'result = await homey.logic.get_variable("__nonexistent_xyz_var__")\n'
            "return str(result)"
        )
        assert r["return_value"] == "None"


class TestSetVariable:
    def test_set_variable_raises_not_supported(self, shs, test_logic_var):
        with pytest.raises(RuntimeError, match="not supported"):
            shs.exec(
                f'await homey.logic.set_variable("{test_logic_var}", "test")'
            )
