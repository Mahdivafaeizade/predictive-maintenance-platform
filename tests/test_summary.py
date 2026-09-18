"""Tests for per-site aggregation."""

from datetime import datetime

from telemetry.ingest import Gap, Measurement
from telemetry.summary import SiteReport, summarise

TS = datetime(2023, 10, 8, 6, 0)


def _measurement(site, sector=1):
    return Measurement(site=site, sector=sector, timestamp=TS, values={"x": 1.0})


def _gap(site, sector=1):
    return Gap(site=site, sector=sector, timestamp=TS)


def test_gap_ratio_is_none_when_a_site_has_no_rows():
    report = SiteReport(site="Site 1", total_rows=0, gap_rows=0)

    assert report.gap_ratio() is None


def test_gap_ratio_is_one_when_every_row_is_a_gap():
    report = SiteReport(site="Site 135", total_rows=3556, gap_rows=3556)

    assert report.gap_ratio() == 1.0
    assert report.measurement_rows() == 0


def test_summarise_counts_each_site_separately():
    rows = [_measurement("Site 36"), _measurement("Site 36"), _gap("Site 135")]

    reports = summarise(rows)

    assert reports["Site 36"].total_rows == 2
    assert reports["Site 36"].gap_rows == 0
    assert reports["Site 135"].gap_ratio() == 1.0


def test_summarise_consumes_a_generator_not_just_a_list():
    rows = (r for r in [_measurement("Site 36"), _gap("Site 36")])

    reports = summarise(rows)

    assert reports["Site 36"].total_rows == 2
    assert reports["Site 36"].gap_ratio() == 0.5
