#!/usr/bin/env bash

# Run from .github/workflows/tests.yml

set -eux -o pipefail

python -m venv "${HOME}/venv"
source "${HOME}/venv/bin/activate"
python -m site
python -m pip install -U pip
echo installing pip packages

python -m pip install "numpy<1.23"  # 1.23 incompatible with numba
python -m pip install xlrd
python -m pip install dogpile.cache==0.9.2  # Later versions incompatible
python -m pip install "SQLAlchemy<1.4"  # _get_immediate_cls_attr moved in 1.4
python -m pip install -e .

pytest
