"""Tests for CSV ingestion: separating real measurements from reporting gaps."""

from datetime import datetime, timezone
from io import StringIO

from telemetry.ingest import Gap, Measurement, read_rows

HEADER = "Base station,Sector,Timestamp,4G data volume DL,4G RB utilization\n"


def test_a_row_with_values_is_a_measurement():
    f = StringIO(HEADER + "Site 36,2,2023-10-08 06:00:00,131.0,2.6\n")

    rows = list(read_rows(f))

    assert len(rows) == 1
    assert isinstance(rows[0], Measurement)
    assert rows[0].site == "Site 36"
    assert rows[0].sector == 2
    assert rows[0].values["4G data volume DL"] == 131.0


def test_an_empty_counter_becomes_none_not_zero():
    f = StringIO(HEADER + "Site 97,2,2023-10-08 06:00:00,0.0,\n")

    rows = list(read_rows(f))

    assert len(rows) == 1
    assert isinstance(rows[0], Measurement)
    assert rows[0].values["4G data volume DL"] == 0.0
    assert rows[0].values["4G RB utilization"] is None


def test_a_row_with_no_measurements_is_a_gap():
    f = StringIO(HEADER + "Site 135,1,2023-10-06 21:15:00,,\n")

    rows = list(read_rows(f))

    assert len(rows) == 1
    assert isinstance(rows[0], Gap)
    assert rows[0].site == "Site 135"
    assert rows[0].sector == 1


def test_the_timestamp_is_parsed_not_left_as_text():
    f = StringIO(HEADER + "Site 36,2,2023-10-08 06:00:00,131.0,2.6\n")

    row = next(read_rows(f))

    assert row.timestamp == datetime(2023, 10, 8, 6, 0, tzinfo=timezone.utc)
    assert row.timestamp.tzinfo is not None, (
        "a naive instant is silently reinterpreted by whoever reads it"
    )


def test_identity_columns_never_appear_among_the_values():
    f = StringIO(HEADER + "Site 36,2,2023-10-08 06:00:00,131.0,2.6\n")

    row = next(read_rows(f))

    assert set(row.values) == {"4G data volume DL", "4G RB utilization"}
