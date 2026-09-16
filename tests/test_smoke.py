"""Smoke test: proves the package is importable and the test runner works."""

import telemetry


def test_package_has_a_version():
    assert telemetry.__version__ == "0.1.0"
