[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tox](https://github.com/codesquadnest/tesla-smart-charger/actions/workflows/tox.yml/badge.svg)](https://github.com/codesquadnest/tesla-smart-charger/actions/workflows/tox.yml)
[![Deploy Documentation](https://github.com/codesquadnest/tesla-smart-charger/actions/workflows/docs.yml/badge.svg)](https://github.com/codesquadnest/tesla-smart-charger/actions/workflows/docs.yml)
![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/codesquadnest/tesla-smart-charger)

# Tesla Smart Charger

Dynamic charging control for your Tesla using the default charger and the Tesla API.

[Official Documentation Page](https://codesquadnest.github.io/tesla-smart-charger/)

## What is the Tesla Smart Charger?

The Tesla Smart Charger is a Python application that allows you to dynamically control the charging of your Tesla vehicle using the Tesla API. The application is designed to be run on a local server, such as a Raspberry Pi, and can be configured to automatically adjust the charging rate of your Tesla based on the current electricity consumption of your home.

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
