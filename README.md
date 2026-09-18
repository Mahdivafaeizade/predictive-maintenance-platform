# RAN Telemetry & Network Health Platform

A platform that ingests performance-management counters from a live mobile
network, validates and stores them, analyses cell behaviour, and flags
degrading cells and unusual load before they become customer-visible problems.

**Status:** Stage 2 — data ingestion and validation. Not yet functional.

## Why this exists

A radio access network reports on itself constantly. Every cell emits counters
every 15 minutes: how loaded it is, what radio quality users report, how many
are connected, how much data moved, how much energy it burned. Buried in that
stream is the answer to questions an operator cares about — which cell is
quietly degrading, which site is burning energy out of proportion to the traffic
it carries, and what load to expect tomorrow.

The counters are already collected. The hard part is turning them into something
trustworthy enough to act on.

## Data

**Performance Management Counters from Live 5G, 4G and 2G Radio Access Network**
— anonymised PM counters from a commercial mobile operator, 15-minute intervals,
sector-level granularity. CC BY 4.0.

    https://doi.org/10.5281/zenodo.17815388

| Archive | Contents |
|---|---|
| `Dataset_01.zip` | LTE 2100 MHz, NR 1800 MHz |
| `Dataset_02.zip` | LTE 1800 MHz, NR 2100 MHz |
| `Dataset_03.zip` | GSM 900, LTE 700/800/1800, NR 2100/3500 MHz |

Every record carries `Base station` (anonymised), `Sector`, and `Timestamp`
(UTC), plus technology-specific counters: utilisation, CQI, RRC and active
users, data volume, MIMO rank, energy consumption.

These are **real operational exports**. Missing and zero values are preserved
exactly as the network produced them. That is the point.

## Architecture (current)

    CSV files  ->  Python ingestion + validation  ->  terminal output

Deliberately minimal. Database, API, containers, and models arrive in later
stages, each when the system actually needs it.

## Requirements

- Python 3.12+
- Git

## Setup

See [docs/setup.md](docs/setup.md) — it covers both Windows and Linux, and what
to do when PyPI is unreachable.

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

## Running the tests

    pytest

## Project layout

    src/telemetry/   application code (an installable package)
    tests/           automated tests
    data/raw/        input data, never committed to git
    docs/            setup guide and learning log

## Roadmap

- [x] Stage 1 - project skeleton
- [ ] Stage 2 - data ingestion and validation
- [ ] Stage 3 - PostgreSQL storage
- [ ] Stage 4 - FastAPI service
- [ ] Stage 5 - ML pipeline
- [ ] Stage 6 - Docker and CI/CD
- [ ] Stage 7 - caching, queues, observability
