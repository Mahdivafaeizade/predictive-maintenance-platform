-- Schema for RAN performance-management counters.
--
-- Three tables, because the source file mixes three different grains in one
-- row. Storing them together would make every SUM() silently wrong, and that is
-- not a hypothetical: it was measured on Dataset_01.

-- ---------------------------------------------------------------------------
-- measurement: one sector, one technology, one 15-minute interval
-- ---------------------------------------------------------------------------
-- The "4G "/"5G " prefix in the export is not data. It repeats what the
-- technology column already says, so it is stripped and the counter names are
-- shared between LTE and NR. That is what lets one table hold both.
--
-- A gap - a row the network was due to report and did not - is kept here with
-- is_gap = true and every counter NULL. Deleting them would erase the evidence
-- that a site went silent, which is precisely what this platform exists to
-- detect. The decision is recorded once, at ingestion, rather than recomputed
-- by every query that has to guess what "all columns NULL" means.

CREATE TABLE IF NOT EXISTS measurement (
    site                TEXT        NOT NULL,
    sector              SMALLINT    NOT NULL,
    measured_at         TIMESTAMPTZ NOT NULL,
    technology          TEXT        NOT NULL CHECK (technology IN ('LTE', 'NR')),
    band_mhz            SMALLINT    NOT NULL,

    is_gap              BOOLEAN     NOT NULL,

    -- NULL means "not reported", never "zero". An idle cell has no resource
    -- block utilisation to report; that is undefined, not 0.0.
    max_active_users_dl DOUBLE PRECISION,
    max_active_users_ul DOUBLE PRECISION,
    data_volume_dl      DOUBLE PRECISION,
    data_volume_ul      DOUBLE PRECISION,
    max_rrc_users       DOUBLE PRECISION,
    rb_utilization      DOUBLE PRECISION,
    cqi_rank_1          DOUBLE PRECISION,
    cqi_rank_2          DOUBLE PRECISION,
    cqi_rank_3          DOUBLE PRECISION,
    cqi_rank_4          DOUBLE PRECISION,
    rrc_users           DOUBLE PRECISION,
    active_users_ul     DOUBLE PRECISION,
    active_users_dl     DOUBLE PRECISION,
    mimo_rank_dl        DOUBLE PRECISION,

    -- A sector cannot report twice for the same technology, band and instant.
    -- Declaring that here makes re-running the loader safe: the conflict is
    -- detected by the database rather than by whoever notices duplicated rows
    -- three weeks later.
    PRIMARY KEY (site, sector, measured_at, technology, band_mhz)
);

-- Time-range queries ("the last week") are the common access pattern, and the
-- primary key starts with site, so it cannot serve them.
CREATE INDEX IF NOT EXISTS measurement_measured_at_idx
    ON measurement (measured_at);

CREATE INDEX IF NOT EXISTS measurement_site_time_idx
    ON measurement (site, measured_at);

-- Gaps are ~2% of rows and almost every quality query filters on them.
-- A partial index covers only the rows that matter, so it stays small.
CREATE INDEX IF NOT EXISTS measurement_gap_idx
    ON measurement (site, measured_at) WHERE is_gap;

-- ---------------------------------------------------------------------------
-- radio_energy: one radio unit, one interval
-- ---------------------------------------------------------------------------
-- Verified on Dataset_01: for all 151,026 overlapping rows, the LTE and NR
-- files report an IDENTICAL radio-unit energy value for the same sector and
-- instant - because one physical radio serves both. Kept in measurement, a
-- query joining the two technologies would count that energy twice.
--
-- Here the grain has no technology column, so the duplicate cannot be stored
-- and therefore cannot be summed.

CREATE TABLE IF NOT EXISTS radio_energy (
    site            TEXT        NOT NULL,
    sector          SMALLINT    NOT NULL,
    measured_at     TIMESTAMPTZ NOT NULL,
    consumption     DOUBLE PRECISION,
    PRIMARY KEY (site, sector, measured_at)
);

-- ---------------------------------------------------------------------------
-- baseband_energy: one baseband unit, one interval
-- ---------------------------------------------------------------------------
-- Verified on Dataset_01: in all 50,343 (site, instant) groups, every sector
-- reports the SAME baseband energy - one baseband serves the whole site.
-- SUM() over sectors would triple it.
--
-- The baseband identifier comes from the directory name in the export
-- (Baseband_02), not from a column. That is a weakness of the source, recorded
-- here rather than hidden.

CREATE TABLE IF NOT EXISTS baseband_energy (
    baseband        TEXT        NOT NULL,
    measured_at     TIMESTAMPTZ NOT NULL,
    consumption     DOUBLE PRECISION,
    PRIMARY KEY (baseband, measured_at)
);
