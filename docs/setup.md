# Setup on a new machine

This project is developed on two machines: a Windows work laptop (PowerShell)
and a Linux personal laptop (bash). Both are first-class. Where they differ,
both commands are given.

## Prerequisites

- Python 3.12 or newer
- Git

Check what you actually have. Do not trust the first answer:

    # Windows / PowerShell
    Get-Command python -All
    python --version
    git --version

    # Linux / bash
    type -a python3
    python3 --version
    git --version

`Get-Command python -All` / `type -a python3` matters: a `python.bat` sitting in
whatever folder you happen to be in will shadow the real interpreter, and
`python --version` will then report a version you did not install.

**On Linux there is usually no bare `python`, only `python3`.** Outside an
activated virtualenv, always type `python3`. Inside one, `python` works.

## Clone and build the environment

    git clone https://github.com/Mahdivafaeizade/predictive-maintenance-platform.git
    cd predictive-maintenance-platform

    # Windows / PowerShell
    python -m venv .venv
    .venv\Scripts\activate

    # Linux / bash
    python3 -m venv .venv
    source .venv/bin/activate

Then, on either machine:

    pip install -e ".[dev]"

After activation the prompt shows `(.venv)`. From that point on, `python` is
unambiguously this project's interpreter - activation puts the venv's script
directory at the front of PATH.

## If PyPI is unreachable

On some networks `pypi.org` times out while the rest of the internet works:

    WARNING: Retrying ... ReadTimeoutError("HTTPSConnectionPool(host='pypi.org',
    port=443): Read timed out.")
    ERROR: Could not find a version that satisfies the requirement setuptools>=68
    ERROR: No matching distribution found for setuptools>=68

That is a **network** failure, not a packaging failure. Confirm before reacting:

    curl -s -o /dev/null -w "%{http_code} %{time_total}\n" https://pypi.org/simple/pytest/

Then point pip at a mirror. Use the environment variable, **not** the
`--index-url` flag:

    # Linux / bash
    export PIP_INDEX_URL=https://mirror-pypi.runflare.com/simple/

    # Windows / PowerShell
    $env:PIP_INDEX_URL = "https://mirror-pypi.runflare.com/simple/"

    pip install -e ".[dev]"

**Why the variable and not the flag:** `pip install -e .` spawns a *child* pip
process to install the build backend (`setuptools`). Command-line flags are not
inherited by that child; environment variables are. With `--index-url` the outer
pip reaches the mirror and the inner one still times out on `pypi.org`.

Mirrors verified reachable from Iran, fastest first:

| Mirror | Operator |
|---|---|
| `https://mirror-pypi.runflare.com/simple/` | Runflare (IR) |
| `https://mirrors.aliyun.com/pypi/simple/` | Alibaba Cloud (CN) |
| `https://pypi.tuna.tsinghua.edu.cn/simple/` | Tsinghua University (CN) |

**Trade-off, understand it before you make it permanent.** A mirror is a
third party that hands you the code you are about to execute. `pip` does not
verify a package against an independent signature, so a hostile or compromised
mirror can serve you a modified package and nothing will warn you. The mitigation
is a lock file with pinned hashes (`pip install --require-hashes`), which the
project will adopt in Stage 6. Until then: keep the mirror as a per-shell
`export`, not a permanent `pip.conf`, so it is a visible decision each time.

## The database

PostgreSQL runs in a container so that the version is pinned, the setup is
identical on both machines, and a broken database can be thrown away and rebuilt
in seconds rather than repaired.

    docker run -d --name pmp-postgres \
      -e POSTGRES_USER=telemetry \
      -e POSTGRES_PASSWORD=devpassword \
      -e POSTGRES_DB=telemetry \
      -p 5433:5432 \
      -v pmp_pgdata:/var/lib/postgresql \
      postgres:18-alpine

Port **5433**, not 5432, because a system PostgreSQL may already hold 5432.
Check before assuming: `ss -tln | grep 5432`.

The mount point is `/var/lib/postgresql`, **not** `/var/lib/postgresql/data`.
Every tutorial written before PostgreSQL 18 says `data`; 18 moved PGDATA to
`/var/lib/postgresql/18/docker` so that `pg_upgrade` can work across versions.
Mounting the old path makes the container refuse to start - correctly, since it
would otherwise run on an empty database while your data sat in an unused volume.
Ask the image, not the internet:

    docker image inspect postgres:18-alpine --format '{{range .Config.Env}}{{println .}}{{end}}'

Wait for it to accept connections, then check:

    docker exec pmp-postgres pg_isready -U telemetry -d telemetry
    docker exec pmp-postgres psql -U telemetry -d telemetry -c '\l'

The container is disposable, the volume is not. `docker rm` loses nothing;
`docker volume rm pmp_pgdata` loses everything.

### If Docker Hub will not serve the image

On some networks the registry authenticates and returns manifests, then stalls
on the layers - the same shape of failure as PyPI above. Pull through a mirror
and retag:

    docker pull docker.arvancloud.ir/library/postgres:18-alpine
    docker tag docker.arvancloud.ir/library/postgres:18-alpine postgres:18-alpine

Mirrors verified to deliver layers: `docker.arvancloud.ir`, `registry.docker.ir`,
`docker.iranserver.com`, `hub.hamdocker.ir`, `docker.mobinhost.com`,
`docker.m.daocloud.io`. The same supply-chain caveat as the PyPI mirror applies:
a registry hands you code you are about to execute. Prefer pinned digests once
the project reaches Stage 6.

## Database settings

The application reads connection settings from the environment - never from a
file inside the repository, and never hard-coded. Copy the template and load it:

    cp .env.example .env
    set -a && source .env && set +a

`set -a` marks subsequent assignments for export, so they become part of the
environment that child processes inherit; `set +a` turns that off again.

`.env` is gitignored. `.env.example` is committed and documents which variables
exist. Never put a real credential in `.env.example`.

Verify the whole chain - Python, network, container, database:

    python -c "from telemetry.db import connect; \
    conn = connect(); print(conn.execute('select current_database()').fetchone()); conn.close()"

## Git identity

A fresh machine has no Git identity, and every commit records one permanently:

    git config --global user.name  "Your Name"
    git config --global user.email "your-email@example.com"
    git config --global init.defaultBranch main

Your commit email is **public** in every pushed commit. To keep a real address
out of the history, use the GitHub-provided no-reply address from
GitHub → Settings → Emails.

## Verify

    pytest

Expect `1 passed`. Read the whole output, not just the last line:

- `platform linux -- Python 3.14.4` - the interpreter actually in use
- `configfile: pyproject.toml` - our config was found and applied
- `collected 1 item` - pytest found the tests; a surprising number means it did not

The two machines run different Python versions (3.13 on Windows, 3.14 on Linux)
and that is intentional: `requires-python = ">=3.12"` is a range, not a pin. If
something breaks on one machine only, the version difference is the first
hypothesis to test.

## Authentication for push

Do NOT create a Personal Access Token and paste it anywhere.

**Windows:** Git for Windows ships Git Credential Manager. The first `git push`
opens a browser, you sign in to GitHub, and the credential is stored encrypted
in Windows Credential Manager. It never travels as plaintext.

**Linux:** there is no Credential Manager. Use an SSH key:

    ssh-keygen -t ed25519 -C "predictive-maintenance-platform"
    cat ~/.ssh/id_ed25519.pub

Paste the **public** key (`.pub` only - the other file never leaves the machine)
into GitHub → Settings → SSH and GPG keys → New SSH key. Then switch the remote:

    git remote set-url origin git@github.com:Mahdivafaeizade/predictive-maintenance-platform.git
    ssh -T git@github.com

A successful test greets you by username. Push then needs no password, ever.

## What is NOT in the repository

`.venv/`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/`, `.env`, and anything
under `data/raw/`. All of it is either generated, machine-specific, or secret.
The build above recreates everything that matters.
