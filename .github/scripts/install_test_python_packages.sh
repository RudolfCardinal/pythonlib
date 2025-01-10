#!/usr/bin/env bash

set -euo pipefail

VENV_DIR=${HOME}/venv

PYTHON=${VENV_DIR}/bin/python
${PYTHON} -m pip install "numpy<1.23"  # 1.23 incompatible with numba
${PYTHON} -m pip install xlrd
${PYTHON} -m pip install dogpile.cache==0.9.2  # Later versions incompatible
${PYTHON} -m pip install pytest
${PYTHON} -m pip install xhtml2pdf weasyprint pdfkit  # For PDF tests
