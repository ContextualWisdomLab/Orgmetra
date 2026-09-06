# Foundation Python compatibility traceability

## Authority

- Repository: `ContextualWisdomLab/Orgmetra`
- Protected parent snapshot: `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`
- Canonical repair issue: #258
- Maturity: `implemented_on_active_pr`

## Finding

Protected Foundation CI executes repository-owned Python quality on CPython 3.14, while several merged
packages declare `requires-python = ">=3.12"`. The Structured Interview Plan work in #40 also declares
Python 3.12 support and carried real Python 3.12/3.13 compatibility jobs in its historical package-local
workflow. Protected #161 correctly retired package-local quality workflows, but adopting that deletion
without replacing the compatibility evidence would silently weaken the declared runtime contract.

A package-local workflow is not restored. The compatibility capability belongs to the existing
`.github/workflows/foundation-ci.yml` owner.

## Decision

Foundation keeps its CPython 3.14 repository-quality lane and adds CPython 3.12 and 3.13 compatibility
lanes on the same pinned `ubuntu-24.04` runner image. Both primary and compatibility package execution
discover `packages/*/pyproject.toml` rather than naming packages in the workflow.

For each compatibility runtime, Foundation reads `project.requires-python` with `tomllib` and
`packaging.specifiers.SpecifierSet`. The selector evaluates that specifier against the actual interpreter
release installed by `actions/setup-python`, using `sys.version_info.major`, `minor`, and `micro`; it does
not fabricate a `.0` patch. A syntactically valid constraint may skip a package only when it excludes that
exact executed interpreter release. Missing, blank, non-string, malformed TOML, or invalid specifier
metadata fails the compatibility job instead of being reclassified as an unsupported runtime. Every
selected package is compiled and its own pytest configuration is executed from its source tree. Package
pytest contracts retain their existing exact statement and branch coverage gates.

The primary CPython 3.14 toolchain remains bound by `.github/requirements/foundation-test.txt`.
CPython 3.12/3.13 use `.github/requirements/foundation-compatibility-test.txt`, installed with
`--require-hashes --no-deps --only-binary=:all:`. The compatibility lock reuses the reviewed versions from
the primary toolchain and binds the reviewed coverage wheels for both compatibility minors.

## Invariants

- `.github/workflows/foundation-ci.yml` remains the repository quality owner.
- Every Foundation job uses `ubuntu-24.04`; `ubuntu-latest` is rejected by executable hygiene checks.
- Compatibility discovery is package-neutral and contains no Interview Plan or Selection Monitoring switch.
- Invalid or missing `project.requires-python` metadata fails closed; only a valid constraint that excludes
  the actual executed interpreter patch may skip one package.
- Patch-sensitive PEP 440 constraints are evaluated against the real interpreter release, never a fabricated
  `major.minor.0` surrogate.
- A compatibility lane fails if no owned package actually declares that runtime supported; static parsing
  cannot satisfy the gate by itself.
- Exact-head checkout and a clean checkout after execution are required in every compatibility lane.
- Repository-local packages are not installed into the checkout as an implicit dependency workaround.
- Package-local quality workflows retired by protected #161 remain retired.

## Scope boundary

This change proves declared compatibility for Python packages under `packages/`. The two HTTP services
currently declare Python 3.11 support but are still exercised by Foundation only on the primary Python
runtime. No Python 3.11 service-compatibility claim is made by this change; that is a separate service
runtime contract rather than evidence for #258 or #40.

## Adoption

After this capability is integrated on protected `develop`, #40 can discard
`.github/workflows/interview-plan-quality.yml`, retain its `requires-python = ">=3.12"` declaration and
package tests, and receive Python 3.12/3.13/3.14 evidence through Foundation without adding a package name
to shared workflow logic. #42 should likewise adopt the protected generic package execution rather than
copying its mutable shared-dispatcher implementation.
