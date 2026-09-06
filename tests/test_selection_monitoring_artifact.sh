#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
package_root="${repository_root}/packages/selection-monitoring"
requirements_path="${repository_root}/.github/requirements/foundation-test.txt"
retired_workflow="${repository_root}/.github/workflows/selection-monitoring-quality.yml"
venv_dir="/tmp/orgmetra-selection-monitoring-venv"

if [[ -e "${retired_workflow}" ]]; then
  printf 'Retired Selection Monitoring leaf workflow must not exist.\n' >&2
  exit 1
fi

rm -rf "${venv_dir}"
python -m venv "${venv_dir}"
"${venv_dir}/bin/python" -m pip install --require-hashes --no-deps --only-binary=:all: -r "${requirements_path}"
"${venv_dir}/bin/python" -m pip check

PYTHONPATH="${package_root}/src" \
COVERAGE_FILE=/tmp/orgmetra-selection-monitoring.coverage \
  "${venv_dir}/bin/python" -m pytest \
  -c "${package_root}/pyproject.toml" \
  "${package_root}/tests"
