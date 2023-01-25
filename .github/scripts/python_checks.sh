#!/usr/bin/env bash

# Run from .github/workflows/python_checks.yml

set -eux -o pipefail

python3 -m venv "${HOME}/venv"
source "${HOME}/venv/bin/activate"
python -m site
python -m pip install -U pip setuptools

echo installing pip packages
python -m pip install -e .
python -m pip install pre-commit

echo running pre-commit checks
pre-commit run --all-files
