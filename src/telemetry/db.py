"""Database connection settings, read from the environment.

Nothing here hard-codes a host or a password. The same code has to run on a
laptop, inside a container, and in CI; only the environment differs. Shipping a
settings file to each of those places is work, while an environment variable is
injected by whatever is already starting the process. That is the whole argument
for reading configuration from the environment rather than from a file.

The defaults describe local development against the container documented in
docs/setup.md, so `connect()` works with nothing set but a password.

PGPASSWORD deliberately has no default. A missing password should stop the
program with a clear message rather than quietly attempt a guess and fail later
with an authentication error that points at the wrong thing.
"""

import os
from urllib.parse import quote

import psycopg

#: Sensible values for local development. Production sets all of these.
DEFAULTS = {
    "PGHOST": "localhost",
    "PGPORT": "5433",
    "PGDATABASE": "telemetry",
    "PGUSER": "telemetry",
}


def connection_string() -> str:
    """Build a libpq connection URI from the current environment.

    Pure: it reads the environment and returns a string, touching no network.
    That is what lets it be tested without a database running.

    Raises:
        RuntimeError: if PGPASSWORD is not set.
    """
    host = os.environ.get("PGHOST", DEFAULTS["PGHOST"])
    port = os.environ.get("PGPORT", DEFAULTS["PGPORT"])
    database = os.environ.get("PGDATABASE", DEFAULTS["PGDATABASE"])
    user = os.environ.get("PGUSER", DEFAULTS["PGUSER"])
    password = os.environ.get("PGPASSWORD")

    if not password:
        raise RuntimeError(
            "PGPASSWORD is not set. Export the development settings first:\n"
            "    set -a && source .env && set +a\n"
            "See docs/setup.md."
        )

    # A URI gives ':' '/' '@' and '?' structural meaning, so any of those inside
    # a username or password would silently break the parse. quote() escapes
    # them. safe="" is required: by default quote() leaves '/' alone.
    return (
        f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/{database}"
    )


def connect() -> psycopg.Connection:
    """Open a connection using the current environment.

    The caller owns the connection and must close it - use it as a context
    manager so that happens even when something raises:

        with connect() as conn:
            ...
    """
    return psycopg.connect(connection_string())
