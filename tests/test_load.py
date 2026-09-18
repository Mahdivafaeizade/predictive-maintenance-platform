"""Tests for loading into PostgreSQL.

Split deliberately into two kinds:

  * unit tests for the pure functions - name normalisation, reading technology
    and band out of a path. They touch nothing and run anywhere.
  * one integration test that needs a real database. It is marked so it can be
    skipped, and it skips itself when no database answers.

Mixing the two is what produces a suite nobody trusts: a red build that means
"the container is not running" teaches people to ignore red builds.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from telemetry.db import connect
from telemetry.load import COUNTERS, counter_key, create_schema, describe, load_file

CSV = (
    "Base station,Sector,Timestamp,Radio unit energy consumption,"
    "Baseband energy consumption,4G data volume DL,4G RB utilization\n"
    "Site 1,1,2023-10-08 06:00:00,25.0,84.0,131.0,2.6\n"
    "Site 1,2,2023-10-08 06:00:00,39.0,84.0,0.0,\n"
    "Site 9,1,2023-10-08 06:00:00,,,,\n"
)


# --------------------------------------------------------------------------
# pure functions
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("column", "expected"),
    [
        ("4G RB utilization", "rb_utilization"),
        ("5G RB utilization", "rb_utilization"),
        ("4G CQI rank 1", "cqi_rank_1"),
        ("4G MIMO rank DL", "mimo_rank_dl"),
        ("4G max active users DL", "max_active_users_dl"),
    ],
)
def test_counter_names_lose_their_technology_prefix(column, expected):
    assert counter_key(column) == expected


def test_lte_and_nr_normalise_to_the_same_name():
    assert counter_key("4G data volume DL") == counter_key("5G data volume DL")


def test_every_normalised_name_is_a_real_column():
    for raw in ("4G RB utilization", "5G CQI rank 4", "4G MIMO rank DL"):
        assert counter_key(raw) in COUNTERS


def test_technology_band_and_baseband_come_from_the_path():
    source = describe(Path("data/raw/Dataset_01/Baseband_02/Dataset_01_NR_1800.csv"))

    assert source.technology == "NR"
    assert source.band_mhz == 1800
    assert source.baseband == "Baseband_02"


def test_an_unrecognised_filename_fails_loudly():
    with pytest.raises(ValueError, match="technology and band"):
        describe(Path("counters.csv"))


# --------------------------------------------------------------------------
# integration
# --------------------------------------------------------------------------


@pytest.fixture
def db():
    """A connection to a scratch schema, rolled back afterwards.

    Skips rather than fails when nothing is listening: an unavailable database
    is an environment fact, not a defect in the code under test.
    """
    try:
        conn = connect()
    except Exception as exc:  # noqa: BLE001 - any connection failure means skip
        pytest.skip(f"no database available: {exc}")

    with conn:
        conn.execute("DROP SCHEMA IF EXISTS pytest_scratch CASCADE")
        conn.execute("CREATE SCHEMA pytest_scratch")
        # Only the scratch schema, never public: with public still on the path,
        # CREATE TABLE IF NOT EXISTS would find the real tables, create nothing,
        # and every test below would quietly write into production data.
        conn.execute("SET search_path TO pytest_scratch")
        conn.commit()

        create_schema(conn)
        yield conn

        conn.execute("SET search_path TO public")
        conn.execute("DROP SCHEMA pytest_scratch CASCADE")
        conn.commit()


@pytest.mark.integration
def test_a_file_lands_in_all_three_tables(db, tmp_path):
    path = tmp_path / "Dataset_99_LTE_2100.csv"
    path.write_text(CSV)

    result = load_file(db, path)

    assert result.measurements == 2
    assert result.gaps == 1

    # Energy is stored once per radio unit, not once per measurement row.
    assert db.execute("select count(*) from radio_energy").fetchone()[0] == 2
    # And once per baseband interval, not once per sector.
    assert db.execute("select count(*) from baseband_energy").fetchone()[0] == 1

    row = db.execute(
        "select rb_utilization, data_volume_dl from measurement"
        " where site = 'Site 1' and sector = 2"
    ).fetchone()
    assert row == (None, 0.0), "an absent counter must stay NULL, never become 0"

    gap = db.execute(
        "select is_gap, rb_utilization from measurement where site = 'Site 9'"
    ).fetchone()
    assert gap == (True, None)


@pytest.mark.integration
def test_loading_the_same_file_twice_changes_nothing(db, tmp_path):
    path = tmp_path / "Dataset_99_LTE_2100.csv"
    path.write_text(CSV)

    load_file(db, path)
    before = db.execute("select count(*) from measurement").fetchone()[0]
    load_file(db, path)
    after = db.execute("select count(*) from measurement").fetchone()[0]

    assert before == after, "the load must be idempotent"


@pytest.mark.integration
def test_timestamps_are_stored_as_instants_not_text(db, tmp_path):
    path = tmp_path / "Dataset_99_LTE_2100.csv"
    path.write_text(CSV)

    load_file(db, path)

    stored = db.execute(
        "select measured_at from measurement where site = 'Site 9'"
    ).fetchone()[0]
    assert stored == datetime(2023, 10, 8, 6, 0, tzinfo=timezone.utc)
