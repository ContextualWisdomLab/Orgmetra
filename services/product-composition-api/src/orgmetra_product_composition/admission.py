"""Fail-closed product-composition admission for released Orgmetra owner APIs.

This module validates immutable routing evidence only. It performs no network I/O,
authentication, HR-domain authorization, database access, or retry execution.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping
from weakref import WeakValueDictionary, finalize

_CONTRACT_SCHEMA = "orgmetra_gateway_composition.v1"
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_RELEASE_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UPSTREAM = re.compile(r"^service://[a-z][a-z0-9-]{1,62}$")
_PATH_PARAMETER = re.compile(r"^\{[a-z][a-z0-9_]{0,63}\}$")
_ROUTE_PATH = re.compile(
    r"^/v[0-9]+(?:/(?:[A-Za-z0-9._:-]+|\{[a-z][a-z0-9_]{0,63}\}))+?$"
)
_RELEASE_LOCATOR = re.compile(
    r"^https://github\.com/ContextualWisdomLab/"
    r"[A-Za-z0-9_.-]+/releases/tag/"
    r"(?P<tag>[A-Za-z0-9][A-Za-z0-9._+-]{0,63})$"
)
_ALLOWED_METHODS = frozenset({"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"})
_FLOATING_RELEASES = frozenset({"develop", "head", "latest", "main", "master"})


class CompositionContractError(ValueError):
    """Reject composition evidence that cannot be admitted without guessing."""


def _exact_text(name: str, value: object, *, maximum: int = 256) -> str:
    if type(value) is not str:
        raise CompositionContractError(f"{name} must be an exact built-in str")
    if not value or len(value) > maximum:
        raise CompositionContractError(f"{name} must contain 1..{maximum} characters")
    return value


def _identifier(name: str, value: object) -> str:
    text = _exact_text(name, value, maximum=64)
    if _IDENTIFIER.fullmatch(text) is None:
        raise CompositionContractError(f"{name} must be lower snake_case")
    return text


def _sha256(name: str, value: object) -> str:
    text = _exact_text(name, value, maximum=64)
    if _SHA256.fullmatch(text) is None:
        raise CompositionContractError(f"{name} must be a lowercase SHA-256 hex digest")
    return text


def _release_version(value: object) -> str:
    text = _exact_text("release_version", value, maximum=64)
    if text.lower() in _FLOATING_RELEASES or text.lower().startswith(("refs/", "pr-")):
        raise CompositionContractError("release_version must identify an immutable release")
    if _RELEASE_VERSION.fullmatch(text) is None:
        raise CompositionContractError("release_version has an unsupported representation")
    return text


def _route_paths_overlap(left: str, right: str) -> bool:
    left_parts = left.strip("/").split("/")
    right_parts = right.strip("/").split("/")
    if len(left_parts) != len(right_parts):
        return False
    for left_part, right_part in zip(left_parts, right_parts, strict=True):
        if left_part == right_part:
            continue
        if _PATH_PARAMETER.fullmatch(left_part) or _PATH_PARAMETER.fullmatch(right_part):
            continue
        return False
    return True


@dataclass(frozen=True, slots=True)
class OwnerApiRelease:
    """Exact released owner API identity required for route admission."""

    service_id: str
    release_version: str
    openapi_sha256: str
    artifact_sha256: str
    release_locator: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "service_id", _identifier("service_id", self.service_id))
        object.__setattr__(self, "release_version", _release_version(self.release_version))
        object.__setattr__(self, "openapi_sha256", _sha256("openapi_sha256", self.openapi_sha256))
        object.__setattr__(self, "artifact_sha256", _sha256("artifact_sha256", self.artifact_sha256))
        locator = _exact_text("release_locator", self.release_locator, maximum=512)
        match = _RELEASE_LOCATOR.fullmatch(locator)
        if match is None:
            raise CompositionContractError("release_locator must name one canonical CWL GitHub Release")
        if match.group("tag") != self.release_version:
            raise CompositionContractError("release_locator must bind the exact release_version")
        object.__setattr__(self, "release_locator", locator)


@dataclass(frozen=True, slots=True)
class CompositionRoute:
    """One product route mapped to one exact released owner API."""

    route_id: str
    path_template: str
    methods: tuple[str, ...]
    owner_release: OwnerApiRelease
    logical_upstream: str
    required: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "route_id", _identifier("route_id", self.route_id))
        path = _exact_text("path_template", self.path_template)
        if _ROUTE_PATH.fullmatch(path) is None or ".." in path:
            raise CompositionContractError("path_template must be a canonical versioned API path")
        object.__setattr__(self, "path_template", path)
        if type(self.methods) is not tuple or not self.methods:
            raise CompositionContractError("methods must be a non-empty exact tuple")
        canonical_methods: list[str] = []
        for method in self.methods:
            text = _exact_text("method", method, maximum=7)
            if text not in _ALLOWED_METHODS:
                raise CompositionContractError("method is not an admitted HTTP method")
            canonical_methods.append(text)
        if len(set(canonical_methods)) != len(canonical_methods):
            raise CompositionContractError("methods must be unique")
        if tuple(sorted(canonical_methods)) != tuple(canonical_methods):
            raise CompositionContractError("methods must use deterministic lexical order")
        if type(self.owner_release) is not OwnerApiRelease:
            raise CompositionContractError("owner_release must be exact OwnerApiRelease evidence")
        upstream = _exact_text("logical_upstream", self.logical_upstream, maximum=80)
        if _UPSTREAM.fullmatch(upstream) is None:
            raise CompositionContractError("logical_upstream must be a service:// reference")
        object.__setattr__(self, "logical_upstream", upstream)
        if type(self.required) is not bool:
            raise CompositionContractError("required must be an exact bool")


def configuration_sha256(routes: tuple["CompositionRoute", ...]) -> str:
    """Hash the canonical semantic route projection, independent of route order."""
    if type(routes) is not tuple or not routes:
        raise CompositionContractError("routes must be a non-empty exact tuple")
    materialized: list[dict[str, object]] = []
    for route in routes:
        if type(route) is not CompositionRoute:
            raise CompositionContractError("routes must contain exact CompositionRoute values")
        owner = route.owner_release
        materialized.append(
            {
                "route_id": route.route_id,
                "path_template": route.path_template,
                "methods": list(route.methods),
                "owner_release": {
                    "service_id": owner.service_id,
                    "release_version": owner.release_version,
                    "openapi_sha256": owner.openapi_sha256,
                    "artifact_sha256": owner.artifact_sha256,
                    "release_locator": owner.release_locator,
                },
                "logical_upstream": route.logical_upstream,
                "required": route.required,
            }
        )
    document = {
        "schema_version": _CONTRACT_SCHEMA,
        "routes": sorted(materialized, key=lambda item: str(item["route_id"])),
    }
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CompositionGeneration:
    """Immutable candidate generation for route admission and rollback identity."""

    schema_version: str
    generation_id: str
    config_sha256: str
    routes: tuple[CompositionRoute, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != _CONTRACT_SCHEMA:
            raise CompositionContractError(f"schema_version must be {_CONTRACT_SCHEMA}")
        object.__setattr__(self, "generation_id", _identifier("generation_id", self.generation_id))
        object.__setattr__(self, "config_sha256", _sha256("config_sha256", self.config_sha256))
        if type(self.routes) is not tuple or not self.routes:
            raise CompositionContractError("routes must be a non-empty exact tuple")
        route_ids: set[str] = set()
        authorities: list[tuple[str, str]] = []
        for route in self.routes:
            if type(route) is not CompositionRoute:
                raise CompositionContractError("routes must contain exact CompositionRoute values")
            if route.route_id in route_ids:
                raise CompositionContractError("route_id values must be unique")
            route_ids.add(route.route_id)
            for method in route.methods:
                for existing_method, existing_path in authorities:
                    if method == existing_method and _route_paths_overlap(
                        route.path_template, existing_path
                    ):
                        raise CompositionContractError("method/path authority must have one owner")
                authorities.append((method, route.path_template))
        expected_config_sha256 = configuration_sha256(self.routes)
        if self.config_sha256 != expected_config_sha256:
            raise CompositionContractError(
                "config_sha256 must match the canonical route materialization"
            )


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class AdmissionReceipt:
    """Canonically issued structural admission evidence, never product authorization."""

    generation_id: str
    config_sha256: str
    admitted_route_ids: tuple[str, ...]
    unavailable_optional_route_ids: tuple[str, ...]

    def __new__(cls, *args: object, **kwargs: object) -> "AdmissionReceipt":
        raise CompositionContractError("AdmissionReceipt is issued only by admit_generation")

    @property
    def required_routes_admitted(self) -> bool:
        """Prove this exact receipt came from canonical required-route admission."""
        _require_canonical_admission_receipt(self)
        return True


def _evaluate_generation(
    generation: CompositionGeneration,
    observed_owner_releases: Mapping[str, OwnerApiRelease],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return canonical route IDs after exact released-owner admission checks."""
    if type(generation) is not CompositionGeneration:
        raise CompositionContractError("generation must be exact CompositionGeneration evidence")
    if type(observed_owner_releases) is not dict:
        raise CompositionContractError("observed_owner_releases must be an exact dict snapshot")

    observed: dict[str, OwnerApiRelease] = {}
    for service_id, release in observed_owner_releases.items():
        canonical_service_id = _identifier("observed service_id", service_id)
        if type(release) is not OwnerApiRelease:
            raise CompositionContractError("observed owner evidence must be exact OwnerApiRelease")
        if canonical_service_id != release.service_id:
            raise CompositionContractError("observed owner key must match release service_id")
        observed[canonical_service_id] = release

    admitted: list[str] = []
    optional_unavailable: list[str] = []
    for route in generation.routes:
        current = observed.get(route.owner_release.service_id)
        if current != route.owner_release:
            if route.required:
                raise CompositionContractError(
                    f"required route {route.route_id} lacks its exact released owner API"
                )
            optional_unavailable.append(route.route_id)
            continue
        admitted.append(route.route_id)

    return tuple(admitted), tuple(optional_unavailable)


def _build_admission_runtime():
    """Build closure-private receipt issuance state plus the canonical evaluator."""
    issued_receipts: WeakValueDictionary[int, AdmissionReceipt] = WeakValueDictionary()
    issued_fields: dict[
        int,
        tuple[str, str, tuple[str, ...], tuple[str, ...]],
    ] = {}

    def require_canonical_admission_receipt(receipt: AdmissionReceipt) -> None:
        """Reject unissued or post-issuance-mutated receipt evidence."""
        receipt_id = id(receipt)
        canonical_fields = issued_fields.get(receipt_id)
        current_fields = (
            receipt.generation_id,
            receipt.config_sha256,
            receipt.admitted_route_ids,
            receipt.unavailable_optional_route_ids,
        )
        if issued_receipts.get(receipt_id) is not receipt or canonical_fields != current_fields:
            raise CompositionContractError("AdmissionReceipt was not canonically issued")

    def admit_generation(
        generation: CompositionGeneration,
        observed_owner_releases: Mapping[str, OwnerApiRelease],
    ) -> AdmissionReceipt:
        """Admit exact owner releases and issue one structural result for this process.

        Optional routes may remain unavailable without invalidating required-route admission.
        A required missing or mismatched owner release fails closed. The returned receipt is
        structural evidence only and is neither HR authorization nor buyer-readiness evidence.
        """

        admitted, optional_unavailable = _evaluate_generation(generation, observed_owner_releases)
        receipt = object.__new__(AdmissionReceipt)
        object.__setattr__(receipt, "generation_id", generation.generation_id)
        object.__setattr__(receipt, "config_sha256", generation.config_sha256)
        object.__setattr__(receipt, "admitted_route_ids", admitted)
        object.__setattr__(receipt, "unavailable_optional_route_ids", optional_unavailable)
        receipt_id = id(receipt)
        issued_receipts[receipt_id] = receipt
        issued_fields[receipt_id] = (
            generation.generation_id,
            generation.config_sha256,
            admitted,
            optional_unavailable,
        )
        finalize(receipt, issued_fields.pop, receipt_id, None)
        return receipt

    return require_canonical_admission_receipt, admit_generation


_require_canonical_admission_receipt, admit_generation = _build_admission_runtime()
