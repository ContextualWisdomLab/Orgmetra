"""Fail closed on ambiguous lookup of immutable verification attempts and failed artifacts."""

from __future__ import annotations

from inspect import signature

from orgmetra_workforce_validation_api.result_nonverifiability import (
    ValidationResultNonVerifiabilityReadPort,
    resolve_validation_result_nonverifiability,
)


_REQUIRED_ATTEMPT_COORDINATES = (
    "verification_attempt_reference",
    "verification_attempt_digest",
)
_REQUIRED_FAILED_ARTIFACT_COORDINATES = (
    "failed_evidence_reference",
    "failed_evidence_digest",
)


def test_resolver_requires_exact_verification_attempt_coordinates() -> None:
    """Bind callers to one immutable attempt instead of an arbitrary matching outcome."""
    parameters = signature(resolve_validation_result_nonverifiability).parameters
    for coordinate in _REQUIRED_ATTEMPT_COORDINATES:
        assert coordinate in parameters


def test_owner_read_port_keys_exact_verification_attempt_coordinates() -> None:
    """Prevent repeated attempts for one result from sharing an ambiguous lookup prefix."""
    parameters = signature(
        ValidationResultNonVerifiabilityReadPort.read_validation_result_nonverifiability
    ).parameters
    for coordinate in _REQUIRED_ATTEMPT_COORDINATES:
        assert coordinate in parameters


def test_non_reproducible_lookup_requires_exact_failed_artifact_coordinates() -> None:
    """Keep same-family failed artifacts distinct before owner resolution."""
    resolver_parameters = signature(resolve_validation_result_nonverifiability).parameters
    port_parameters = signature(
        ValidationResultNonVerifiabilityReadPort.read_validation_result_nonverifiability
    ).parameters
    for coordinate in _REQUIRED_FAILED_ARTIFACT_COORDINATES:
        assert coordinate in resolver_parameters
        assert coordinate in port_parameters


def test_attempt_release_time_remains_owner_evidence_not_lookup_authority() -> None:
    """Keep release chronology owner-resolved while the immutable attempt identity is exact."""
    resolver_parameters = signature(resolve_validation_result_nonverifiability).parameters
    port_parameters = signature(
        ValidationResultNonVerifiabilityReadPort.read_validation_result_nonverifiability
    ).parameters
    assert "verification_attempt_released_at" not in resolver_parameters
    assert "verification_attempt_released_at" not in port_parameters


def test_failed_artifact_release_time_remains_owner_evidence_not_lookup_authority() -> None:
    """Require artifact identity without accepting caller-supplied release chronology."""
    resolver_parameters = signature(resolve_validation_result_nonverifiability).parameters
    port_parameters = signature(
        ValidationResultNonVerifiabilityReadPort.read_validation_result_nonverifiability
    ).parameters
    assert "failed_evidence_released_at" not in resolver_parameters
    assert "failed_evidence_released_at" not in port_parameters
