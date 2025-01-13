#!/usr/bin/env bash

set -euo pipefail

SYSTEM_PYTHON=python3

if [ $# -eq 1 ]; then
    # Script needs at least Python 3.10 for docs. Allow this to be specified
    SYSTEM_PYTHON=$1
fi

VENV_DIR=${HOME}/venv

${SYSTEM_PYTHON} -m venv "${VENV_DIR}"
PYTHON=${VENV_DIR}/bin/python
${PYTHON} -VV
${PYTHON} -m site
${PYTHON} -m pip install -U pip setuptools
echo Dumping pre-installed packages
${PYTHON} -m pip freeze
