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

_CONTRACT_SCHEMA = "orgmetra_gateway_composition.v1"
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_RELEASE_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UPSTREAM = re.compile(r"^service://[a-z][a-z0-9-]{1,62}$")
_ROUTE_PATH = re.compile(r"^/v[0-9]+(?:/[A-Za-z0-9._{}:-]+)+$")
_ALLOWED_METHODS = frozenset({"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"})
_ALLOWED_RETRY_CLASSES = frozenset({"never", "safe", "owner_idempotent"})
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
        if not locator.startswith("https://github.com/ContextualWisdomLab/") or "/releases/tag/" not in locator:
            raise CompositionContractError("release_locator must name a canonical CWL GitHub Release")
        if not locator.endswith(f"/{self.release_version}"):
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
    retry_class: str

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
        retry_class = _exact_text("retry_class", self.retry_class, maximum=32)
        if retry_class not in _ALLOWED_RETRY_CLASSES:
            raise CompositionContractError("retry_class is not governed")
        object.__setattr__(self, "retry_class", retry_class)


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
                "retry_class": route.retry_class,
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
        route_keys: set[tuple[str, str]] = set()
        for route in self.routes:
            if type(route) is not CompositionRoute:
                raise CompositionContractError("routes must contain exact CompositionRoute values")
            if route.route_id in route_ids:
                raise CompositionContractError("route_id values must be unique")
            route_ids.add(route.route_id)
            for method in route.methods:
                key = (method, route.path_template)
                if key in route_keys:
                    raise CompositionContractError("method/path authority must have one owner")
                route_keys.add(key)
        expected_config_sha256 = configuration_sha256(self.routes)
        if self.config_sha256 != expected_config_sha256:
            raise CompositionContractError(
                "config_sha256 must match the canonical route materialization"
            )


@dataclass(frozen=True, slots=True)
class AdmissionReceipt:
    """Structural route-admission result; it is not HR authorization evidence."""

    generation_id: str
    config_sha256: str
    admitted_route_ids: tuple[str, ...]
    unavailable_optional_route_ids: tuple[str, ...]

    @property
    def buyer_ready(self) -> bool:
        """A returned receipt means every required route passed exact release admission."""
        return True


def admit_generation(
    generation: CompositionGeneration,
    observed_owner_releases: Mapping[str, OwnerApiRelease],
) -> AdmissionReceipt:
    """Admit routes only when observed owner releases exactly match configured evidence.

    Optional routes may remain unavailable without making the required product surface
    unready. A required missing or mismatched owner release fails closed.
    """

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

    return AdmissionReceipt(
        generation_id=generation.generation_id,
        config_sha256=generation.config_sha256,
        admitted_route_ids=tuple(admitted),
        unavailable_optional_route_ids=tuple(optional_unavailable),
    )
