# Setup on a new machine

Everything below assumes Windows + PowerShell. On Linux/macOS the only
difference is the activate command.

## Prerequisites

- Python 3.12 or newer
- Git

Check what you actually have. Do not trust the first answer:

    Get-Command python -All
    python --version
    git --version

`Get-Command python -All` matters: a `python.bat` sitting in whatever folder you
happen to be in will shadow the real interpreter, and `python --version` will
then report a version you did not install.

## Clone and build the environment

    git clone https://github.com/Mahdivafaeizade/predictive-maintenance-platform.git
    cd predictive-maintenance-platform
    python -m venv .venv
    .venv\Scripts\activate
    pip install -e ".[dev]"

On Linux/macOS the activate line is `source .venv/bin/activate`.

After activation the prompt shows `(.venv)`. From that point on, `python` is
unambiguously this project's interpreter - activation puts `.venv\Scripts` at
the front of PATH.

## Verify

    pytest

Expect `1 passed`. Read the whole output, not just the last line:

- `platform ... Python 3.13.1` - the interpreter actually in use
- `configfile: pyproject.toml` - our config was found and applied
- `collected N items` - pytest found the tests; a surprising N means it did not

## Authentication for push

Do NOT create a Personal Access Token and paste it anywhere.

Git for Windows ships Git Credential Manager. The first `git push` opens a
browser, you sign in to GitHub, and the credential is stored encrypted in
Windows Credential Manager. It never travels as plaintext.

    git push

If a prompt is suppressed and push fails with "Invalid username or token", the
terminal you are in may have interactive prompts disabled. Run the push from a
plain PowerShell window instead.

## What is NOT in the repository

`.venv/`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/`, `.env`, and anything
under `data/raw/`. All of it is either generated, machine-specific, or secret.
The build above recreates everything that matters.
