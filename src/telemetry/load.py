"""Load parsed rows into PostgreSQL.

The export encodes three facts in places other than the columns:

  * technology and band live in the file name  (Dataset_01_LTE_2100.csv)
  * the baseband identifier lives in the directory name  (Baseband_02/)
  * the "4G "/"5G " prefix on every counter repeats the technology

So loading is not a straight column-to-column copy. It normalises the counter
names, lifts the three implicit facts into real columns, and splits each source
row across the three tables that hold its three different grains.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import psycopg

from telemetry.ingest import Gap, Measurement, read_rows

SCHEMA_PATH = Path(__file__).parent / "sql" / "schema.sql"

RADIO_ENERGY = "Radio unit energy consumption"
BASEBAND_ENERGY = "Baseband energy consumption"

#: Counter columns of `measurement`, in the order the INSERT expects them.
COUNTERS = (
    "max_active_users_dl",
    "max_active_users_ul",
    "data_volume_dl",
    "data_volume_ul",
    "max_rrc_users",
    "rb_utilization",
    "cqi_rank_1",
    "cqi_rank_2",
    "cqi_rank_3",
    "cqi_rank_4",
    "rrc_users",
    "active_users_ul",
    "active_users_dl",
    "mimo_rank_dl",
)

#: Dataset_01_LTE_2100.csv -> ('LTE', 2100)
_FILENAME = re.compile(r"_(LTE|NR|GSM)_(\d+)\.csv$", re.IGNORECASE)


@dataclass(frozen=True)
class Source:
    """What the export's file layout says about a file's contents."""

    path: Path
    technology: str
    band_mhz: int
    baseband: str


@dataclass(frozen=True)
class LoadResult:
    """What one load actually wrote."""

    measurements: int
    gaps: int
    radio_energy: int
    baseband_energy: int

    def rows(self) -> int:
        return self.measurements + self.gaps


def counter_key(column: str) -> str:
    """Normalise an export column name to a schema column name.

    '4G RB utilization'  -> 'rb_utilization'
    '5G RB utilization'  -> 'rb_utilization'
    '4G CQI rank 1'      -> 'cqi_rank_1'

    Stripping the prefix is what lets LTE and NR share one table: it carries no
    information the `technology` column does not already hold.
    """
    name = re.sub(r"^[45]G ", "", column)
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def describe(path: Path) -> Source:
    """Read technology, band and baseband out of the file and directory names.

    Raises:
        ValueError: if the name does not match the export's convention. Failing
            here is deliberate - guessing a band would put wrong data in a
            column nobody would ever think to re-check.
    """
    match = _FILENAME.search(path.name)
    if match is None:
        raise ValueError(
            f"cannot read technology and band from {path.name!r}; "
            "expected something like Dataset_01_LTE_2100.csv"
        )
    technology, band = match.group(1).upper(), int(match.group(2))
    return Source(
        path=path, technology=technology, band_mhz=band, baseband=path.parent.name
    )


def create_schema(conn: psycopg.Connection) -> None:
    """Apply schema.sql. Safe to repeat - every statement is IF NOT EXISTS."""
    conn.execute(SCHEMA_PATH.read_text())
    conn.commit()


_INSERT_MEASUREMENT = f"""
    INSERT INTO measurement (
        site, sector, measured_at, technology, band_mhz, is_gap,
        {", ".join(COUNTERS)}
    ) VALUES ({", ".join(["%s"] * (6 + len(COUNTERS)))})
    ON CONFLICT DO NOTHING
"""

_INSERT_RADIO = """
    INSERT INTO radio_energy (site, sector, measured_at, consumption)
    VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING
"""

_INSERT_BASEBAND = """
    INSERT INTO baseband_energy (baseband, measured_at, consumption)
    VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
"""


def load_file(
    conn: psycopg.Connection, path: Path, batch_size: int = 5_000
) -> LoadResult:
    """Stream one CSV into the database.

    Rows are sent in batches rather than one at a time: each round trip to the
    server costs a network hop, and 151,026 of them is minutes of pure waiting.
    Memory stays flat because only `batch_size` rows are held at once - the
    generator from read_rows is never materialised.

    Re-running this is safe. Every insert carries ON CONFLICT DO NOTHING, so a
    load interrupted half way can simply be run again. That property has a name:
    the operation is idempotent.
    """
    source = describe(path)
    measurements = gaps = radio = baseband = 0
    m_batch: list[tuple] = []
    r_batch: list[tuple] = []
    b_batch: list[tuple] = []

    def flush() -> None:
        with conn.cursor() as cur:
            if m_batch:
                cur.executemany(_INSERT_MEASUREMENT, m_batch)
            if r_batch:
                cur.executemany(_INSERT_RADIO, r_batch)
            if b_batch:
                cur.executemany(_INSERT_BASEBAND, b_batch)
        m_batch.clear()
        r_batch.clear()
        b_batch.clear()

    with open(path, newline="") as f:
        for row in read_rows(f):
            is_gap = isinstance(row, Gap)
            values = (
                {} if is_gap else {counter_key(k): v for k, v in row.values.items()}
            )

            m_batch.append(
                (
                    row.site,
                    row.sector,
                    row.timestamp,
                    source.technology,
                    source.band_mhz,
                    is_gap,
                    *(values.get(name) for name in COUNTERS),
                )
            )
            gaps += is_gap
            measurements += not is_gap

            if isinstance(row, Measurement):
                # Energy rows are written only when a value exists. A NULL row
                # would claim we measured and got nothing, which is a different
                # statement from not having measured at all.
                if (value := row.values.get(RADIO_ENERGY)) is not None:
                    r_batch.append((row.site, row.sector, row.timestamp, value))
                    radio += 1
                if (value := row.values.get(BASEBAND_ENERGY)) is not None:
                    b_batch.append((source.baseband, row.timestamp, value))
                    baseband += 1

            if len(m_batch) >= batch_size:
                flush()

    flush()
    conn.commit()
    return LoadResult(measurements, gaps, radio, baseband)
