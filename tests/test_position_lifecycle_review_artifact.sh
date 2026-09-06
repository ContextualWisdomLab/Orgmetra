#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
package_root="${repository_root}/packages/position-lifecycle-review"
requirements_path="${repository_root}/.github/requirements/foundation-test.txt"
retired_workflow="${repository_root}/.github/workflows/position-lifecycle-review-quality.yml"
build_requirement="/tmp/orgmetra-position-lifecycle-review-build.txt"
build_tree="/tmp/orgmetra-position-lifecycle-review-build-tree"
dist_dir="/tmp/orgmetra-position-lifecycle-review-dist"
venv_dir="/tmp/orgmetra-position-lifecycle-review-venv"
install_requirement="/tmp/orgmetra-position-lifecycle-review-install.txt"

if [[ -e "${retired_workflow}" ]]; then
  printf 'Retired Position Lifecycle Review leaf workflow must not exist.\n' >&2
  exit 1
fi

python - <<'PY'
import sys

if sys.version_info[:3] != (3, 14, 7):
    raise SystemExit(f"Position Lifecycle Review quality requires CPython 3.14.7, got {sys.version}")
PY

printf '%s\n' 'setuptools==84.0.0 --hash=sha256:51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670' > "${build_requirement}"
python -m pip install --require-hashes --no-deps --only-binary=:all: -r "${build_requirement}"

rm -rf "${build_tree}" "${dist_dir}" "${venv_dir}"
cp -a "${package_root}" "${build_tree}"
mkdir -p "${dist_dir}"
python -m pip wheel --no-deps --no-build-isolation --wheel-dir "${dist_dir}" "${build_tree}"

mapfile -t wheels < <(find "${dist_dir}" -maxdepth 1 -type f -name '*.whl' -print)
if [[ "${#wheels[@]}" -ne 1 ]]; then
  printf 'Position Lifecycle Review build must produce exactly one wheel.\n' >&2
  exit 1
fi
wheel_path="${wheels[0]}"
wheel_sha="$(sha256sum "${wheel_path}" | awk '{print $1}')"

python -m venv "${venv_dir}"
"${venv_dir}/bin/python" -m pip install --require-hashes --no-deps --only-binary=:all: -r "${requirements_path}"
printf 'orgmetra-position-lifecycle-review[test] @ file://%s --hash=sha256:%s\n' "${wheel_path}" "${wheel_sha}" > "${install_requirement}"
"${venv_dir}/bin/python" -m pip install --require-hashes --no-deps -r "${install_requirement}"
"${venv_dir}/bin/python" -m pip check

"${venv_dir}/bin/python" - <<'PY'
from importlib.metadata import metadata
from pathlib import Path

import coverage
import pytest
import pytest_cov
import orgmetra_position_lifecycle_review

venv_root = Path("/tmp/orgmetra-position-lifecycle-review-venv").resolve()
module_path = Path(orgmetra_position_lifecycle_review.__file__).resolve()
if not module_path.is_relative_to(venv_root):
    raise SystemExit(f"package imported outside isolated environment: {module_path}")
for module in (coverage, pytest, pytest_cov):
    dependency_path = Path(module.__file__).resolve()
    if not dependency_path.is_relative_to(venv_root):
        raise SystemExit(f"test dependency imported outside isolated environment: {dependency_path}")
if "test" not in (metadata("orgmetra-position-lifecycle-review").get_all("Provides-Extra") or []):
    raise SystemExit("built distribution does not expose the reviewed test extra")
PY

cd /tmp
COVERAGE_FILE=/tmp/orgmetra-position-lifecycle-review.coverage \
  "${venv_dir}/bin/python" -m pytest \
  -c "${package_root}/pyproject.toml" \
  "${package_root}/tests"
