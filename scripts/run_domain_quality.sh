#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="packages/orgmetra-domain/src"
python -m compileall -q packages/orgmetra-domain/src packages/orgmetra-domain/tests tests
python -m coverage erase
python -m coverage run --branch --source=orgmetra_domain -m unittest discover \
  -s packages/orgmetra-domain/tests -v
python -m coverage report --show-missing --fail-under=100
python tests/validate_docstrings.py
python -m unittest discover -s tests -p 'test_*.py' -v
