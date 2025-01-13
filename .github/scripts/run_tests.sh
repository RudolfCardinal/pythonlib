#!/usr/bin/env bash

# Run from .github/workflows/tests.yml

set -euo pipefail

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_ROOT_DIR=${THIS_DIR}/../..
VENV_DIR=${HOME}/venv
PYTEST=${VENV_DIR}/bin/pytest

sudo apt-get install wkhtmltopdf

cd "${PROJECT_ROOT_DIR}"

# pytest --log-cli-level=INFO
${PYTEST}
