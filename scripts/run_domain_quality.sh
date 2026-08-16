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

artifact_root="$(mktemp -d)"
trap 'rm -rf "${artifact_root}"' EXIT
wheel_dir="${artifact_root}/wheel"
install_dir="${artifact_root}/installed"
smoke_dir="${artifact_root}/smoke"
mkdir -p "${wheel_dir}" "${install_dir}" "${smoke_dir}"

python -m pip wheel \
  --no-deps \
  --no-build-isolation \
  --wheel-dir "${wheel_dir}" \
  packages/orgmetra-domain
wheel_path="$(find "${wheel_dir}" -maxdepth 1 -type f -name 'orgmetra_domain-*.whl' -print -quit)"
if [[ -z "${wheel_path}" ]]; then
    echo "orgmetra-domain wheel was not produced" >&2
    exit 1
fi

python - "${wheel_path}" <<'PY'
from pathlib import Path
import sys
import zipfile

wheel_path = Path(sys.argv[1])
with zipfile.ZipFile(wheel_path) as archive:
    if "orgmetra_domain/py.typed" not in archive.namelist():
        raise SystemExit("built wheel is missing orgmetra_domain/py.typed")
PY

python -m pip install --no-deps --target "${install_dir}" "${wheel_path}"
(
    cd "${smoke_dir}"
    unset PYTHONPATH
    PYTHONNOUSERSITE=1 python - "${install_dir}" <<'PY'
from pathlib import Path
import sys

installed = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(installed))
import orgmetra_domain

module_path = Path(orgmetra_domain.__file__).resolve()
if installed not in module_path.parents:
    raise SystemExit(f"smoke import did not use installed wheel: {module_path}")
PY
)
