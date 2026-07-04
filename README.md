# Tesla Smart Charger

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tox](https://github.com/codesquadnest/tesla-smart-charger/actions/workflows/tox.yml/badge.svg)](https://github.com/codesquadnest/tesla-smart-charger/actions/workflows/tox.yml)
[![Deploy Documentation](https://github.com/codesquadnest/tesla-smart-charger/actions/workflows/docs.yml/badge.svg)](https://github.com/codesquadnest/tesla-smart-charger/actions/workflows/docs.yml)
![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/codesquadnest/tesla-smart-charger)

Dynamic charging control for one or more Tesla vehicles, using the built-in charger and the Tesla Fleet API.

[Official Documentation Page](https://codesquadnest.github.io/tesla-smart-charger/)

## What is the Tesla Smart Charger?

The Tesla Smart Charger is a Python application that dynamically controls the charging of your Tesla vehicles based on your home's live power consumption. It runs on a local server, such as a Raspberry Pi, and throttles charging when your home approaches its circuit limit — so you never trip the main breaker.

## Features (v2)

- **Multi-vehicle** — manage several Teslas from one install, each with its own charge limits and priority.
- **Guided onboarding** — a 10-step OAuth 2.0 + PKCE wizard; no manual `config.json` editing.
- **React dashboard** — live status, per-vehicle controls, overload history, and settings.
- **Overload strategies** — reduce charging **proportionally** across vehicles or by **priority** order.

## Getting started

- **New install:** follow the [Quick start](https://codesquadnest.github.io/tesla-smart-charger/quick-start.html) guide.
- **Upgrading from v1:** follow the [Migration guide](docs/migration.md).

In short:

```sh
git clone https://github.com/codesquadnest/tesla-smart-charger.git
cd tesla-smart-charger
# Generate certs into certs/ (see the Quick start), then:
docker compose up --build -d
# Open the dashboard at http://<server-ip>:8000 and follow the onboarding wizard.
```

## How to Contribute

We welcome contributions to enhance the functionality and features of Tesla Smart Charger. If you're interested in contributing, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Install `uv` if you haven't already:

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

4. Create and activate a virtual environment using `uv`:

   ```sh
   uv venv .venv
   source .venv/bin/activate
   ```

5. Sync dependencies using `uv`:

   ```sh
   uv sync
   ```

6. Install additional Python versions if needed:

   ```sh
   uv py install <python-version>
   ```

7. Add the following to your PATH to ensure binaries can be found:

   ```sh
   export PATH="/home/$USER/.local/bin:${PATH}"
   ```

8. Run tests with `tox`:

   ```sh
   tox
   ```

9. Implement your changes.
10. Test your changes thoroughly.
11. Create a pull request with a clear description of your changes.

**Feel free to contribute and help make Tesla Smart Charger even better!**
