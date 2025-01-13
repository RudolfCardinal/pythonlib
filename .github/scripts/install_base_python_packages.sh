#!/usr/bin/env bash

set -euo pipefail

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_ROOT_DIR=${THIS_DIR}/../..
VENV_DIR=${HOME}/venv

PYTHON=${VENV_DIR}/bin/python
echo Installing pip packages
${PYTHON} -m pip install -e "${PROJECT_ROOT_DIR}"
