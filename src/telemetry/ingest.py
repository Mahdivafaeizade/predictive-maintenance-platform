"""Read RAN performance-management counters from a CSV export.

The export mixes two different things in one file, and telling them apart is
the whole point of this module:

  * A **measurement** - the network reported counters for one sector in one
    15-minute window. Individual counters may still be absent, which means the
    metric was undefined for that window, not that it was zero. An idle cell
    has no resource-block utilisation to report; that is not the same as
    utilisation being zero.

  * A **gap** - the row exists and names a sector and a time, but carries no
    counters at all. The collection system knew a measurement was due and had
    nothing to record. In Dataset_01 every such row belongs to Site 135, which
    never reported anything for the 18.5 days it appears.

Collapsing the two - `fillna(0)` being the usual way - invents readings that
never happened. A site that was powered and merely failed to report becomes a
site that consumed no energy.
"""

import csv
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime

#: Columns that identify a row rather than measure anything. Always populated,
#: even in rows that carry no counters - which is what makes a gap recordable.
IDENTITY_COLUMNS = ("Base station", "Sector", "Timestamp")

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class Measurement:
    """Counters reported for one sector during one interval.

    `values` maps the counter name exactly as the export spells it to its
    value, or to None where the counter was not reported. Keeping it as a dict
    rather than named fields lets one parser handle both the 4G and 5G exports,
    whose columns differ only by prefix.
    """

    site: str
    sector: int
    timestamp: datetime
    values: dict[str, float | None]


@dataclass(frozen=True)
class Gap:
    """An interval the network was due to report and did not."""

    site: str
    sector: int
    timestamp: datetime


def _to_float(raw: str) -> float | None:
    """Convert one CSV field; an empty field means 'not reported'.

    Checking for emptiness *before* converting is deliberate: float("") raises
    ValueError, so the absence has to be recognised at the boundary rather than
    discovered by a crash further in.
    """
    raw = raw.strip()
    if raw == "":
        return None
    return float(raw)


def read_rows(lines: Iterable[str]) -> Iterator[Measurement | Gap]:
    """Yield one Measurement or Gap per data row.

    Takes any iterable of CSV lines - an open file, a StringIO, a list - so
    that callers stay free to decide where the bytes come from, and tests need
    no files on disk.

    This is a generator: rows are produced one at a time and memory stays flat
    regardless of file size. Dataset_03 is 709 MB.
    """
    for row in csv.DictReader(lines):
        values = {
            name: _to_float(raw)
            for name, raw in row.items()
            if name not in IDENTITY_COLUMNS
        }

        site = row["Base station"]
        sector = int(row["Sector"])
        timestamp = datetime.strptime(row["Timestamp"], TIMESTAMP_FORMAT)

        if all(value is None for value in values.values()):
            yield Gap(site=site, sector=sector, timestamp=timestamp)
        else:
            yield Measurement(
                site=site, sector=sector, timestamp=timestamp, values=values
            )
