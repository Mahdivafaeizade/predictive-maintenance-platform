# Predictive Maintenance Platform

A sensor telemetry platform that ingests readings from industrial machines,
validates and stores them, analyses them, and predicts equipment failure
before it happens.

**Status:** Stage 1 — project skeleton. Not yet functional.

## Why this exists

Unplanned machine failure is expensive: production stops, and emergency
repairs cost more than scheduled ones. Sensors on a machine (temperature,
vibration, current draw) change measurably before a failure. This platform
captures those signals and learns to warn ahead of time.

## Architecture (current)

    CSV file  ->  Python script  ->  terminal output

Deliberately minimal. Database, API, containers, and models are added in
later stages, each when the system actually needs it.

## Requirements

- Python 3.12+
- Git

## Setup

    python -m venv .venv
    .venv\Scripts\activate
    pip install -e ".[dev]"

## Running the tests

    pytest

## Project layout

    src/telemetry/   application code (an installable package)
    tests/           automated tests
    data/raw/        input data, never committed to git

## Roadmap

- [x] Stage 1 - project skeleton
- [ ] Stage 2 - data ingestion and validation
- [ ] Stage 3 - PostgreSQL storage
- [ ] Stage 4 - FastAPI service
- [ ] Stage 5 - ML pipeline
- [ ] Stage 6 - Docker and CI/CD
