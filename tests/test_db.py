"""Tests for connection settings.

None of these need a running database: connection_string() only reads the
environment and formats a string, so it can be tested anywhere. A test that
silently requires a container to be up is a test that fails on someone else's
machine for reasons that have nothing to do with the code.
"""

import pytest

from telemetry.db import connection_string

# Applied by every test so the developer's own environment cannot leak in.
PG_VARS = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD")


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in PG_VARS:
        monkeypatch.delenv(name, raising=False)


def test_values_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("PGHOST", "db.internal")
    monkeypatch.setenv("PGPORT", "6000")
    monkeypatch.setenv("PGDATABASE", "prod")
    monkeypatch.setenv("PGUSER", "reader")
    monkeypatch.setenv("PGPASSWORD", "s3cret")

    assert connection_string() == "postgresql://reader:s3cret@db.internal:6000/prod"


def test_local_defaults_apply_when_nothing_is_set(monkeypatch):
    monkeypatch.setenv("PGPASSWORD", "devpassword")

    assert connection_string() == (
        "postgresql://telemetry:devpassword@localhost:5433/telemetry"
    )


def test_a_missing_password_fails_loudly():
    with pytest.raises(RuntimeError, match="PGPASSWORD"):
        connection_string()


def test_special_characters_in_the_password_are_escaped(monkeypatch):
    monkeypatch.setenv("PGPASSWORD", "p@ss/word:1")

    assert "p%40ss%2Fword%3A1" in connection_string()
