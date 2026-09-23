from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    ActivationEvent,
    ActivationRegistryError,
    CompositionGeneration,
    CompositionRoute,
    DeploymentIdentity,
    OwnerApiRelease,
    RecoveredActivation,
    configuration_sha256,
)


def _generation() -> CompositionGeneration:
    owner = OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256="1" * 64,
        artifact_sha256="2" * 64,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )
    route = CompositionRoute(
        route_id="people_get",
        path_template="/v1/people/{person_record_id}",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )
    return CompositionGeneration(
        generation_id="generation_one",
        routes=(route,),
        config_sha256=configuration_sha256((route,)),
    )


def _event(generation: CompositionGeneration) -> ActivationEvent:
    return ActivationEvent(
        deployment=DeploymentIdentity("orgmetra_gateway", "production"),
        activation_sequence=1,
        generation_id=generation.generation_id,
        previous_generation_id=None,
        event_kind="activate",
        evidence_bundle_sha256="a" * 64,
    )


def test_recovered_activation_accepts_absent_or_positive_durable_recovery_sequence() -> None:
    generation = _generation()
    event = _event(generation)

    assert RecoveredActivation(event, generation).recovery_sequence is None
    assert RecoveredActivation(event, generation, recovery_sequence=1).recovery_sequence == 1


@pytest.mark.parametrize("recovery_sequence", [True, 0, -1])
def test_recovered_activation_rejects_invalid_durable_recovery_sequence(
    recovery_sequence,
) -> None:
    generation = _generation()

    with pytest.raises(ActivationRegistryError, match="recovery_sequence"):
        RecoveredActivation(
            _event(generation),
            generation,
            recovery_sequence=recovery_sequence,
        )
