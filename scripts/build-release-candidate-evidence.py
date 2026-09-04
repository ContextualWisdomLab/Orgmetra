#!/usr/bin/env python3
"""Build reproducible, unsigned release-candidate evidence for one Orgmetra commit.

The builder reads blobs directly from the exact Git commit instead of copying the
working tree. It emits a deterministic source archive, a CycloneDX 1.7 SBOM, and
an in-toto Statement v1 carrying a SLSA provenance v1 predicate. The provenance
is intentionally unsigned candidate evidence; a later protected release process
must provide any trusted signing or platform attestation required for release.
"""

from __future__ import annotations

import argparse
import binascii
from collections import defaultdict
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import struct
import subprocess
import tarfile
import tomllib
from typing import Any, Iterable
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

_REPOSITORY_URL = "https://github.com/ContextualWisdomLab/Orgmetra"
_REPOSITORY_GIT_URI = "git+https://github.com/ContextualWisdomLab/Orgmetra.git"
_EXPECTED_PYTHON_RUNTIME = "3.14.7"
_EXPECTED_PYTHON_IMPLEMENTATION = "CPython"
_COMPRESSION_IMPLEMENTATION = "orgmetra-stored-gzip-v1"
_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_PYTHON_REQUIREMENT_PATTERN = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]+\])?\s*(?P<constraint>[^;]*)"
)
_PYTHON_VERSION_PATTERN = re.compile(
    r"""
    ^\s*v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?
        (?P<release>[0-9]+(?:\.[0-9]+)*)
        (?P<pre>
            [-_.]?
            (?P<pre_l>a|b|c|rc|alpha|beta|pre|preview)
            [-_.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_.]?
                (?P<post_l>post|rev|r)
                [-_.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>
            [-_.]?
            (?P<dev_l>dev)
            [-_.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)
_SEMVER_NUMBER = r"(?:0|[1-9][0-9]*)"
_SEMVER_PRERELEASE_IDENTIFIER = (
    r"(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
)
_NPM_EXACT_VERSION_PATTERN = re.compile(
    rf"^(?P<version>{_SEMVER_NUMBER}\.{_SEMVER_NUMBER}\.{_SEMVER_NUMBER}"
    rf"(?:-{_SEMVER_PRERELEASE_IDENTIFIER}(?:\.{_SEMVER_PRERELEASE_IDENTIFIER})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)$"
)
_ALLOWED_GIT_MODES = frozenset({"100644", "100755", "120000"})
_DEPENDENCY_SCOPE_PRIORITY = {"excluded": 0, "optional": 1, "required": 2}


class ReleaseEvidenceError(RuntimeError):
    """Report a fail-closed release-evidence construction error."""


def _run_git(arguments: list[str]) -> bytes:
    """Run one read-only Git command in the repository and return raw stdout."""
    result = subprocess.run(
        ["git", *arguments],
        cwd=_repository_root(),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReleaseEvidenceError(f"git {' '.join(arguments)} failed: {diagnostic}")
    return result.stdout


def _repository_root() -> Path:
    """Return the repository root containing this checked-in builder."""
    return Path(__file__).resolve().parents[1]


def _validate_runtime() -> None:
    """Require the exact CPython patch runtime that defines evidence bytes."""
    observed_runtime = platform.python_version()
    observed_implementation = platform.python_implementation()
    if (
        observed_runtime != _EXPECTED_PYTHON_RUNTIME
        or observed_implementation != _EXPECTED_PYTHON_IMPLEMENTATION
    ):
        raise ReleaseEvidenceError(
            "release evidence runtime mismatch: "
            f"expected={_EXPECTED_PYTHON_IMPLEMENTATION} {_EXPECTED_PYTHON_RUNTIME}, "
            f"observed={observed_implementation} {observed_runtime}"
        )


def _validate_source_sha(source_sha: str) -> None:
    """Require the requested source SHA to be the exact checked-out commit."""
    if type(source_sha) is not str or _SHA_PATTERN.fullmatch(source_sha) is None:
        raise ReleaseEvidenceError("source SHA must be one lowercase 40-character Git SHA")
    head = _run_git(["rev-parse", "HEAD"]).decode("ascii").strip()
    if head != source_sha:
        raise ReleaseEvidenceError(
            f"source SHA must equal the exact checkout HEAD: requested={source_sha}, head={head}"
        )


def _tree_entries(source_sha: str) -> list[tuple[str, str, str, str]]:
    """Return normalized blob metadata for every tracked path in the commit."""
    raw = _run_git(["ls-tree", "-r", "-z", "--full-tree", source_sha])
    entries: list[tuple[str, str, str, str]] = []
    for raw_entry in raw.split(b"\0"):
        if not raw_entry:
            continue
        try:
            metadata, raw_path = raw_entry.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ")
            path = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            raise ReleaseEvidenceError("Git tree contains an unsupported path or metadata entry") from error
        normalized = PurePosixPath(path)
        if (
            normalized.is_absolute()
            or ".." in normalized.parts
            or path != normalized.as_posix()
            or not path
        ):
            raise ReleaseEvidenceError(f"Git tree path is not a safe normalized relative path: {path!r}")
        if object_type != "blob" or mode not in _ALLOWED_GIT_MODES:
            raise ReleaseEvidenceError(
                f"release source tree contains unsupported Git object mode/type: {path} {mode} {object_type}"
            )
        if _SHA_PATTERN.fullmatch(object_id) is None:
            raise ReleaseEvidenceError(f"Git tree contains an invalid blob identity for {path}")
        entries.append((path, mode, object_type, object_id))
    if not entries:
        raise ReleaseEvidenceError("release source tree must contain at least one tracked file")
    return sorted(entries, key=lambda entry: entry[0])


def _blob_bytes(object_id: str) -> bytes:
    """Read one blob by immutable Git object identity."""
    return _run_git(["cat-file", "blob", object_id])


def _deterministic_gzip(content: bytes) -> bytes:
    """Encode RFC 1952 gzip bytes without delegating DEFLATE output to host zlib."""
    if type(content) is not bytes:
        raise ReleaseEvidenceError("deterministic gzip content must be exact bytes")

    encoded = bytearray(b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff")
    if not content:
        encoded.extend(b"\x01\x00\x00\xff\xff")
    else:
        for offset in range(0, len(content), 65535):
            block = content[offset : offset + 65535]
            is_final = offset + len(block) == len(content)
            encoded.append(0x01 if is_final else 0x00)
            block_size = len(block)
            encoded.extend(struct.pack("<H", block_size))
            encoded.extend(struct.pack("<H", 0xFFFF - block_size))
            encoded.extend(block)

    crc32 = binascii.crc32(content) & 0xFFFFFFFF
    encoded.extend(struct.pack("<II", crc32, len(content) & 0xFFFFFFFF))
    return bytes(encoded)


def _build_source_archive(
    source_sha: str,
    entries: Iterable[tuple[str, str, str, str]],
) -> bytes:
    """Create a deterministic gzip-compressed GNU tar archive of the exact tree."""
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.GNU_FORMAT) as archive:
        for path, mode, _object_type, object_id in entries:
            content = _blob_bytes(object_id)
            info = tarfile.TarInfo(name=path)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            if mode == "120000":
                try:
                    link_target = content.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise ReleaseEvidenceError(f"symbolic link target is not UTF-8: {path}") from error
                if "\x00" in link_target:
                    raise ReleaseEvidenceError(f"symbolic link target contains NUL: {path}")
                info.type = tarfile.SYMTYPE
                info.mode = 0o777
                info.size = 0
                info.linkname = link_target
                archive.addfile(info)
                continue
            info.mode = 0o755 if mode == "100755" else 0o644
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return _deterministic_gzip(tar_buffer.getvalue())


def _sha256_bytes(data: bytes) -> str:
    """Return a lowercase SHA-256 digest for immutable evidence bytes."""
    return hashlib.sha256(data).hexdigest()


def _canonical_json(document: dict[str, Any]) -> bytes:
    """Serialize one evidence document with deterministic UTF-8 JSON bytes."""
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _python_name(name: str) -> str:
    """Normalize a Python distribution name for stable package references."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _pypi_ref(name: str, version: str | None, requirement: str | None = None) -> str:
    """Return a deterministic Python bom-ref, digesting non-exact declarations."""
    normalized_name = _python_name(name)
    if version:
        return f"pkg:pypi/{quote(normalized_name, safe='-._~')}@{quote(version, safe='-._~')}"
    if type(requirement) is not str or not requirement:
        raise ReleaseEvidenceError("non-exact Python dependency must preserve its full requirement")
    requirement_digest = hashlib.sha256(requirement.encode("utf-8")).hexdigest()[:16]
    return f"urn:orgmetra:pypi-requirement:{normalized_name}:{requirement_digest}"


def _npm_package_path(name: str) -> str:
    """Encode an npm name using separate canonical namespace and package segments."""
    if name.startswith("@"):
        scope, separator, package_name = name.partition("/")
        if not separator or len(scope) == 1 or not package_name or "/" in package_name:
            raise ReleaseEvidenceError("scoped npm package name must use @scope/name")
        return f"{quote(scope, safe='-._~')}/{quote(package_name, safe='-._~')}"
    if "/" in name:
        raise ReleaseEvidenceError("unscoped npm package name must not contain a slash")
    return quote(name, safe="-._~")


def _npm_ref(name: str, version: str | None, requirement: str) -> str:
    """Return a deterministic npm bom-ref without pretending a range is a version."""
    encoded_name = _npm_package_path(name)
    if version:
        return f"pkg:npm/{encoded_name}@{quote(version, safe='-._~')}"
    requirement_digest = hashlib.sha256(requirement.encode("utf-8")).hexdigest()[:16]
    return f"urn:orgmetra:npm-requirement:{encoded_name}:{requirement_digest}"


def _normalize_python_version(candidate: str) -> str | None:
    """Normalize one concrete PEP 440 version using the specification's accepted spellings."""
    match = _PYTHON_VERSION_PATTERN.fullmatch(candidate)
    if match is None:
        return None

    epoch_number = int(match.group("epoch") or "0")
    normalized = f"{epoch_number}!" if epoch_number else ""
    normalized += ".".join(str(int(part)) for part in match.group("release").split("."))

    pre_label = match.group("pre_l")
    if pre_label is not None:
        pre_aliases = {
            "a": "a",
            "alpha": "a",
            "b": "b",
            "beta": "b",
            "c": "rc",
            "rc": "rc",
            "pre": "rc",
            "preview": "rc",
        }
        normalized += pre_aliases[pre_label.lower()]
        normalized += str(int(match.group("pre_n") or "0"))

    if match.group("post") is not None:
        post_number = match.group("post_n1") or match.group("post_n2") or "0"
        normalized += f".post{int(post_number)}"

    if match.group("dev") is not None:
        normalized += f".dev{int(match.group('dev_n') or '0')}"

    local = match.group("local")
    if local is not None:
        local_parts = re.split(r"[-_.]", local.lower())
        normalized_local = ".".join(
            str(int(part)) if part.isdigit() else part for part in local_parts
        )
        normalized += f"+{normalized_local}"
    return normalized


def _python_requirement(requirement: str) -> tuple[str, str | None]:
    """Extract the distribution name and normalized exact pin when unconditional and concrete."""
    match = _PYTHON_REQUIREMENT_PATTERN.match(requirement)
    if match is None:
        raise ReleaseEvidenceError(f"unsupported Python dependency declaration: {requirement!r}")
    name = match.group("name")
    constraint = match.group("constraint").strip()
    if ";" in requirement or not constraint.startswith("==") or constraint.startswith("==="):
        return name, None
    candidate = constraint[2:].strip()
    if not candidate or "*" in candidate:
        return name, None
    return name, _normalize_python_version(candidate)


def _add_component(
    components: dict[str, dict[str, Any]],
    component: dict[str, Any],
) -> None:
    """Add one component and fail if one bom-ref would describe different evidence."""
    component_ref = component.get("bom-ref")
    if not isinstance(component_ref, str) or not component_ref:
        raise ReleaseEvidenceError("CycloneDX component must have a non-empty bom-ref")
    previous = components.get(component_ref)
    if previous is not None and previous != component:
        raise ReleaseEvidenceError(f"conflicting CycloneDX component evidence for {component_ref}")
    components[component_ref] = component


def _merge_dependency_component(
    components: dict[str, dict[str, Any]],
    component: dict[str, Any],
) -> None:
    """Merge repeated declarations or a local package identity without losing evidence."""
    component_ref = component.get("bom-ref")
    if not isinstance(component_ref, str) or not component_ref:
        raise ReleaseEvidenceError("CycloneDX component must have a non-empty bom-ref")
    previous = components.get(component_ref)
    if previous is None:
        _add_component(components, component)
        return

    identity_fields = {
        key: value
        for key, value in previous.items()
        if key not in {"scope", "properties", "type"}
    }
    candidate_identity = {
        key: value
        for key, value in component.items()
        if key not in {"scope", "properties", "type"}
    }
    if component_ref.startswith("pkg:pypi/"):
        previous_name = identity_fields.get("name")
        candidate_name = candidate_identity.get("name")
        if type(previous_name) is not str or type(candidate_name) is not str:
            raise ReleaseEvidenceError(
                f"Python dependency component must have a string name for {component_ref}"
            )
        identity_fields["name"] = _python_name(previous_name)
        candidate_identity["name"] = _python_name(candidate_name)
    if identity_fields != candidate_identity:
        raise ReleaseEvidenceError(f"conflicting CycloneDX component evidence for {component_ref}")

    previous_scope = previous.get("scope")
    candidate_scope = component.get("scope")
    if candidate_scope not in _DEPENDENCY_SCOPE_PRIORITY:
        raise ReleaseEvidenceError(
            f"dependency component has invalid CycloneDX scope for {component_ref}"
        )
    if previous_scope is None:
        merged_scope = candidate_scope
    elif previous_scope not in _DEPENDENCY_SCOPE_PRIORITY:
        raise ReleaseEvidenceError(
            f"dependency component has invalid CycloneDX scope for {component_ref}"
        )
    else:
        merged_scope = max(
            (previous_scope, candidate_scope),
            key=lambda scope: _DEPENDENCY_SCOPE_PRIORITY[scope],
        )

    merged_properties: set[tuple[str, str]] = set()
    for source in (previous, component):
        properties = source.get("properties")
        if not isinstance(properties, list):
            raise ReleaseEvidenceError(
                f"dependency component properties must be a list for {component_ref}"
            )
        for property_row in properties:
            if not isinstance(property_row, dict):
                raise ReleaseEvidenceError(
                    f"dependency component property must be an object for {component_ref}"
                )
            name = property_row.get("name")
            value = property_row.get("value")
            if type(name) is not str or not name or type(value) is not str:
                raise ReleaseEvidenceError(
                    f"dependency component property must be string evidence for {component_ref}"
                )
            merged_properties.add((name, value))

    merged = dict(previous)
    merged["scope"] = merged_scope
    merged["properties"] = [
        {"name": name, "value": value}
        for name, value in sorted(merged_properties)
    ]
    components[component_ref] = merged


def _build_sbom(
    source_sha: str,
    archive_digest: str,
    tree_content: dict[str, bytes],
) -> bytes:
    """Build a deterministic CycloneDX 1.7 source/dependency inventory."""
    components: dict[str, dict[str, Any]] = {}
    dependency_edges: dict[str, set[str]] = defaultdict(set)
    local_refs: list[str] = []
    deferred_python_dependencies: list[tuple[str, list[str], str]] = []
    deferred_npm_dependencies: list[tuple[str, dict[str, str], str]] = []

    for path in sorted(tree_content):
        content = tree_content[path]
        if path.endswith("pyproject.toml"):
            try:
                document = tomllib.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
                raise ReleaseEvidenceError(f"cannot parse project metadata: {path}") from error
            project = document.get("project")
            if not isinstance(project, dict):
                continue
            name = project.get("name")
            version = project.get("version")
            if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
                raise ReleaseEvidenceError(f"project metadata must declare name and version: {path}")
            component_ref = _pypi_ref(name, version)
            _add_component(
                components,
                {
                    "type": "library",
                    "bom-ref": component_ref,
                    "name": name,
                    "version": version,
                    "purl": component_ref,
                    "properties": [{"name": "orgmetra:source:path", "value": path}],
                },
            )
            local_refs.append(component_ref)
            dependencies = project.get("dependencies", [])
            if not isinstance(dependencies, list) or any(type(item) is not str for item in dependencies):
                raise ReleaseEvidenceError(f"project dependencies must be a string array: {path}")
            deferred_python_dependencies.append((component_ref, dependencies, "required"))

            optional_dependencies = project.get("optional-dependencies", {})
            if not isinstance(optional_dependencies, dict):
                raise ReleaseEvidenceError(
                    f"project optional-dependencies must be a table of string arrays: {path}"
                )
            for group_name in sorted(optional_dependencies):
                group_requirements = optional_dependencies[group_name]
                if (
                    type(group_name) is not str
                    or not group_name
                    or not isinstance(group_requirements, list)
                    or any(type(item) is not str for item in group_requirements)
                ):
                    raise ReleaseEvidenceError(
                        f"project optional-dependencies must be a table of string arrays: {path}"
                    )
                deferred_python_dependencies.append(
                    (component_ref, group_requirements, "optional")
                )

            build_system = document.get("build-system", {})
            build_requirements = (
                build_system.get("requires", [])
                if isinstance(build_system, dict)
                else []
            )
            if not isinstance(build_requirements, list) or any(
                type(item) is not str for item in build_requirements
            ):
                raise ReleaseEvidenceError(f"build-system requires must be a string array: {path}")
            deferred_python_dependencies.append(
                (component_ref, build_requirements, "excluded")
            )

        if path.endswith("package.json"):
            try:
                document = json.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ReleaseEvidenceError(f"cannot parse package metadata: {path}") from error
            if not isinstance(document, dict):
                raise ReleaseEvidenceError(f"package metadata must be an object: {path}")
            name = document.get("name")
            version = document.get("version")
            if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
                continue
            component_ref = _npm_ref(name, version, version)
            _add_component(
                components,
                {
                    "type": "application" if path == "package.json" else "library",
                    "bom-ref": component_ref,
                    "name": name,
                    "version": version,
                    "purl": component_ref,
                    "properties": [{"name": "orgmetra:source:path", "value": path}],
                },
            )
            local_refs.append(component_ref)
            for field_name, scope in (
                ("dependencies", "required"),
                ("optionalDependencies", "optional"),
                ("devDependencies", "excluded"),
            ):
                dependencies = document.get(field_name, {})
                if not isinstance(dependencies, dict) or any(
                    type(dep_name) is not str or type(dep_requirement) is not str
                    for dep_name, dep_requirement in dependencies.items()
                ):
                    raise ReleaseEvidenceError(f"{field_name} must be a string map: {path}")
                deferred_npm_dependencies.append((component_ref, dependencies, scope))

    for parent_ref, requirements, scope in deferred_python_dependencies:
        for requirement in requirements:
            name, version = _python_requirement(requirement)
            component_ref = _pypi_ref(name, version, requirement)
            component = {
                "type": "library",
                "bom-ref": component_ref,
                "name": name,
                "scope": scope,
                "properties": [
                    {"name": "orgmetra:declared-requirement", "value": requirement}
                ],
            }
            if version:
                component["version"] = version
                component["purl"] = component_ref
            _merge_dependency_component(components, component)
            dependency_edges[parent_ref].add(component_ref)

    for parent_ref, dependencies, scope in deferred_npm_dependencies:
        for name, requirement in sorted(dependencies.items()):
            exact_match = _NPM_EXACT_VERSION_PATTERN.fullmatch(requirement.strip())
            version = exact_match.group("version") if exact_match else None
            component_ref = _npm_ref(name, version, requirement)
            component = {
                "type": "library",
                "bom-ref": component_ref,
                "name": name,
                "scope": scope,
                "properties": [
                    {"name": "orgmetra:declared-requirement", "value": requirement}
                ],
            }
            if version:
                component["version"] = version
                component["purl"] = component_ref
            _merge_dependency_component(components, component)
            dependency_edges[parent_ref].add(component_ref)

    if not local_refs:
        raise ReleaseEvidenceError(
            "source tree must expose at least one package metadata component"
        )

    root_ref = f"urn:orgmetra:source:{source_sha}"
    root_component = {
        "type": "application",
        "bom-ref": root_ref,
        "name": "orgmetra",
        "version": f"0.1.0+git.{source_sha[:12]}",
        "hashes": [{"alg": "SHA-256", "content": archive_digest}],
        "properties": [
            {"name": "orgmetra:source:git-sha", "value": source_sha},
            {"name": "orgmetra:evidence:scope", "value": "release-candidate-source"},
        ],
    }
    dependency_edges[root_ref].update(local_refs)
    dependency_rows = [
        {"ref": component_ref, "dependsOn": sorted(children)}
        for component_ref, children in sorted(dependency_edges.items())
    ]
    for component_ref in sorted(components):
        if component_ref not in dependency_edges:
            dependency_rows.append({"ref": component_ref, "dependsOn": []})
    dependency_rows.sort(key=lambda row: row["ref"])

    serial = uuid5(NAMESPACE_URL, f"{_REPOSITORY_URL}@{source_sha}")
    document: dict[str, Any] = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {"component": root_component},
        "components": [components[key] for key in sorted(components)],
        "dependencies": dependency_rows,
    }
    return _canonical_json(document)


def _builder_identity(source_sha: str) -> tuple[str, str]:
    """Return the execution-mode builder URI without mislabeling local evidence."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return (
            f"{_REPOSITORY_URL}/actions/workflows/release-candidate-evidence-quality.yml",
            "github-actions",
        )
    return (
        f"{_REPOSITORY_URL}/blob/{source_sha}/docs/traceability/"
        "release-candidate-evidence.md#local-builder-v1",
        "local",
    )


def _build_provenance(
    source_sha: str,
    archive_name: str,
    archive_digest: str,
    sbom_digest: str,
) -> bytes:
    """Build unsigned in-toto Statement v1 / SLSA provenance v1 candidate evidence."""
    build_type_uri = (
        f"{_REPOSITORY_URL}/blob/{source_sha}/docs/traceability/"
        "release-candidate-evidence.md#build-type-v1"
    )
    builder_id, builder_environment = _builder_identity(source_sha)
    document: dict[str, Any] = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {"name": archive_name, "digest": {"sha256": archive_digest}},
            {"name": "orgmetra.cdx.json", "digest": {"sha256": sbom_digest}},
        ],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": build_type_uri,
                "externalParameters": {
                    "repository": _REPOSITORY_URL,
                    "sourceRevision": source_sha,
                },
                "internalParameters": {
                    "archiveFormat": "tar+gzip",
                    "archiveMtime": 0,
                    "builderEnvironment": builder_environment,
                    "compressionImplementation": _COMPRESSION_IMPLEMENTATION,
                    "cycloneDxSpecVersion": "1.7",
                    "pythonImplementation": _EXPECTED_PYTHON_IMPLEMENTATION,
                    "pythonRuntime": _EXPECTED_PYTHON_RUNTIME,
                },
                "resolvedDependencies": [
                    {
                        "uri": _REPOSITORY_GIT_URI,
                        "digest": {"gitCommit": source_sha},
                    }
                ],
            },
            "runDetails": {"builder": {"id": builder_id}},
        },
    }
    return _canonical_json(document)


def _write_file(output_directory: Path, name: str, content: bytes) -> None:
    """Write one candidate artifact inside the caller-selected output directory."""
    output_directory.mkdir(parents=True, exist_ok=True)
    target = output_directory / name
    if target.parent != output_directory:
        raise ReleaseEvidenceError(f"unsafe release evidence output name: {name}")
    target.write_bytes(content)


def build_release_candidate_evidence(output_directory: Path, source_sha: str) -> None:
    """Generate deterministic source, SBOM, and unsigned provenance evidence."""
    _validate_runtime()
    _validate_source_sha(source_sha)
    entries = _tree_entries(source_sha)
    tree_content = {
        path: _blob_bytes(object_id)
        for path, _mode, _kind, object_id in entries
    }
    archive = _build_source_archive(source_sha, entries)
    archive_name = f"orgmetra-source-{source_sha}.tar.gz"
    archive_digest = _sha256_bytes(archive)
    sbom = _build_sbom(source_sha, archive_digest, tree_content)
    provenance = _build_provenance(
        source_sha,
        archive_name,
        archive_digest,
        _sha256_bytes(sbom),
    )
    _write_file(output_directory, archive_name, archive)
    _write_file(output_directory, "orgmetra.cdx.json", sbom)
    _write_file(output_directory, "orgmetra.provenance.json", provenance)


def _parse_arguments() -> argparse.Namespace:
    """Parse the intentionally small release-evidence command interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-sha", required=True)
    return parser.parse_args()


def main() -> int:
    """Run the release-candidate evidence builder and return a process status."""
    arguments = _parse_arguments()
    try:
        build_release_candidate_evidence(
            arguments.output_dir.resolve(),
            arguments.source_sha,
        )
    except (OSError, ReleaseEvidenceError) as error:
        print(f"release candidate evidence failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
