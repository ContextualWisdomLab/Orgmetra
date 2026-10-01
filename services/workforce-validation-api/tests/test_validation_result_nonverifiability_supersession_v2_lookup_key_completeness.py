"""Fail closed when v2 exact-artifact correction lookup omits predecessor artifact identity."""

from inspect import signature

from orgmetra_workforce_validation_api.result_nonverifiability_supersession_v2_authority import (
    ValidationResultNonVerifiabilitySupersessionV2AuthorityReadPort,
    resolve_validation_result_nonverifiability_supersession_v2_authority,
)


_REQUIRED_FAILED_ARTIFACT_COORDINATES = (
    "failed_evidence_reference",
    "failed_evidence_digest",
)


def test_v2_resolver_requires_exact_failed_artifact_coordinates() -> None:
    """Bind callers to the immutable failed artifact that the v2 correction supersedes."""
    parameters = signature(
        resolve_validation_result_nonverifiability_supersession_v2_authority
    ).parameters
    for coordinate in _REQUIRED_FAILED_ARTIFACT_COORDINATES:
        assert coordinate in parameters


def test_v2_owner_read_port_keys_exact_failed_artifact_coordinates() -> None:
    """Prevent same-family artifacts from sharing an ambiguous v2 owner lookup prefix."""
    parameters = signature(
        ValidationResultNonVerifiabilitySupersessionV2AuthorityReadPort.read_validation_result_nonverifiability_supersession_v2_authority
    ).parameters
    for coordinate in _REQUIRED_FAILED_ARTIFACT_COORDINATES:
        assert coordinate in parameters


def test_failed_artifact_release_time_remains_owner_evidence() -> None:
    """Keep failed-artifact chronology owner-resolved once reference and digest are exact."""
    resolver_parameters = signature(
        resolve_validation_result_nonverifiability_supersession_v2_authority
    ).parameters
    port_parameters = signature(
        ValidationResultNonVerifiabilitySupersessionV2AuthorityReadPort.read_validation_result_nonverifiability_supersession_v2_authority
    ).parameters
    assert "failed_evidence_released_at" not in resolver_parameters
    assert "failed_evidence_released_at" not in port_parameters
