#!/usr/bin/env bash

# Run from .github/workflows/python_checks.yml

set -euo pipefail

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_ROOT_DIR=${THIS_DIR}/../..
VENV_DIR=${HOME}/venv
PYTHON=${VENV_DIR}/bin/python
PRECOMMIT=${VENV_DIR}/bin/pre-commit

cd "${PROJECT_ROOT_DIR}"

echo Installing pre-commit
${PYTHON} -m pip install -e .
${PYTHON} -m pip install pre-commit

echo Running pre-commit checks
${PRECOMMIT} run --all-files
