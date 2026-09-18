"""Aggregate parsed rows into per-site reporting statistics.

Kept separate from `ingest` on purpose: ingestion decides what a row *is*,
this module decides what a collection of rows *means*. Two responsibilities,
two modules, two sets of tests.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from telemetry.ingest import Gap, Measurement


@dataclass(frozen=True)
class SiteReport:
    """How completely one site reported over the period examined."""

    site: str
    total_rows: int
    gap_rows: int

    def measurement_rows(self) -> int:
        """Rows that carried at least one counter."""
        return self.total_rows - self.gap_rows

    def gap_ratio(self) -> float | None:
        """Fraction of this site's rows that carried no counters at all.

        None when the site has no rows: a ratio with no denominator is
        undefined, not zero. Returning 0.0 here would claim the site reported
        perfectly, which is the opposite of what an empty site means - the
        same trap as filling an absent counter with zero.
        """
        if self.total_rows == 0:
            return None
        return self.gap_rows / self.total_rows


def summarise(rows: Iterable[Measurement | Gap]) -> dict[str, SiteReport]:
    """Count measurements and gaps for each site.

    Consumes the iterable once, so it works directly on the generator from
    `read_rows` without materialising the file.
    """
    totals: Counter[str] = Counter()
    gaps: Counter[str] = Counter()

    for row in rows:
        totals[row.site] += 1
        if isinstance(row, Gap):
            gaps[row.site] += 1

    return {
        site: SiteReport(site=site, total_rows=total, gap_rows=gaps[site])
        for site, total in totals.items()
    }
