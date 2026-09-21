from __future__ import annotations

from dataclasses import replace

import pytest

from orgmetra_product_composition import (
    AdmissionReceipt,
    CompositionContractError,
    CompositionGeneration,
    CompositionRoute,
    OwnerApiRelease,
    admit_generation,
    configuration_sha256,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64


def release(service_id: str = "people_api") -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id=service_id,
        release_version="v1.2.3",
        openapi_sha256=A,
        artifact_sha256=B,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )


def route(
    *,
    route_id: str = "people_history",
    service_id: str = "people_api",
    path: str = "/v1/tenants/{tenant_record_id}/people/{person_record_id}",
    methods: tuple[str, ...] = ("GET",),
    required: bool = True,
) -> CompositionRoute:
    return CompositionRoute(
        route_id=route_id,
        path_template=path,
        methods=methods,
        owner_release=release(service_id),
        logical_upstream=f"service://{service_id.replace('_', '-')}",
        required=required,
    )


def generation(*routes: CompositionRoute) -> CompositionGeneration:
    selected_routes = routes or (route(),)
    return CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_001",
        config_sha256=configuration_sha256(selected_routes),
        routes=selected_routes,
    )


def test_admits_exact_required_release_and_reports_optional_unavailable() -> None:
    required_route = route()
    optional_route = route(
        route_id="validation_read",
        service_id="workforce_validation_api",
        path="/v1/validation/studies/{study_id}",
        required=False,
    )
    receipt = admit_generation(
        generation(required_route, optional_route),
        {"people_api": required_route.owner_release},
    )

    assert receipt.required_routes_admitted is True
    assert receipt.generation_id == "generation_001"
    assert receipt.config_sha256 == configuration_sha256((required_route, optional_route))
    assert receipt.admitted_route_ids == ("people_history",)
    assert receipt.unavailable_optional_route_ids == ("validation_read",)


def test_required_release_must_match_every_coordinate() -> None:
    expected = route()
    mismatched = replace(expected.owner_release, artifact_sha256=D)
    with pytest.raises(CompositionContractError, match="lacks its exact released owner API"):
        admit_generation(generation(expected), {"people_api": mismatched})
    with pytest.raises(CompositionContractError, match="lacks its exact released owner API"):
        admit_generation(generation(expected), {})


def test_owner_release_rejects_mutable_or_ambiguous_coordinates() -> None:
    base = dict(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256=A,
        artifact_sha256=B,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )
    for version in ("latest", "main", "refs/heads/main", "pr-17", "bad version"):
        with pytest.raises(CompositionContractError):
            OwnerApiRelease(**(base | {"release_version": version}))
    for field, value in (
        ("service_id", "People-API"),
        ("openapi_sha256", "A" * 64),
        ("artifact_sha256", "x" * 64),
        ("release_locator", "https://example.com/people-api/releases/tag/v1.2.3"),
    ):
        with pytest.raises(CompositionContractError):
            OwnerApiRelease(**(base | {field: value}))
    with pytest.raises(CompositionContractError):
        OwnerApiRelease(
            **(
                base
                | {
                    "release_locator": "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.4"
                }
            )
        )


def test_route_rejects_ambiguous_routing_and_non_owner_evidence() -> None:
    valid = route()
    invalid_cases = (
        {"route_id": "Bad-Route"},
        {"path_template": "v1/people"},
        {"path_template": "/v1/../people"},
        {"path_template": "/v1/people/{}"},
        {"path_template": "/v1/people/{Person}"},
        {"path_template": "/v1/people/{person"},
        {"methods": []},
        {"methods": ("GET", "GET")},
        {"methods": ("POST", "GET")},
        {"methods": ("TRACE",)},
        {"logical_upstream": "https://people-api"},
        {"required": 1},
        {"owner_release": object()},
    )
    for changes in invalid_cases:
        with pytest.raises(CompositionContractError):
            CompositionRoute(
                route_id=changes.get("route_id", valid.route_id),
                path_template=changes.get("path_template", valid.path_template),
                methods=changes.get("methods", valid.methods),
                owner_release=changes.get("owner_release", valid.owner_release),
                logical_upstream=changes.get("logical_upstream", valid.logical_upstream),
                required=changes.get("required", valid.required),
            )


def test_generation_rejects_bad_schema_shape_and_duplicate_authority() -> None:
    first = route()
    second = route(route_id="people_history_alias")
    for kwargs in (
        {"schema_version": "v1"},
        {"generation_id": "bad-id"},
        {"config_sha256": "0"},
        {"routes": []},
        {"routes": (object(),)},
        {"routes": (first, first)},
        {"routes": (first, second)},
    ):
        values = dict(
            schema_version="orgmetra_gateway_composition.v1",
            generation_id="generation_001",
            config_sha256=configuration_sha256((first,)),
            routes=(first,),
        )
        values.update(kwargs)
        with pytest.raises(CompositionContractError):
            CompositionGeneration(**values)


def test_observed_snapshot_is_exact_and_keyed_by_release_identity() -> None:
    expected = route()
    gen = generation(expected)
    with pytest.raises(CompositionContractError, match="exact CompositionGeneration"):
        admit_generation(object(), {})
    with pytest.raises(CompositionContractError, match="exact dict snapshot"):
        admit_generation(gen, [])  # type: ignore[arg-type]


def test_observed_snapshot_rejects_bad_keys_values_and_mismatched_key() -> None:
    gen = generation()
    with pytest.raises(CompositionContractError):
        admit_generation(gen, {"Bad-Key": release()})
    with pytest.raises(CompositionContractError):
        admit_generation(gen, {"people_api": object()})  # type: ignore[dict-item]
    with pytest.raises(CompositionContractError):
        admit_generation(gen, {"job_analysis_api": release("people_api")})


def test_exact_builtin_scalar_guards_reject_subclasses_and_empty_text() -> None:
    class Text(str):
        pass

    base = release()
    with pytest.raises(CompositionContractError):
        replace(base, service_id=Text("people_api"))
    with pytest.raises(CompositionContractError):
        replace(base, release_locator="")


def test_configuration_digest_is_order_stable_and_binds_route_semantics() -> None:
    first = route()
    second = route(
        route_id="validation_read",
        service_id="workforce_validation_api",
        path="/v1/validation/studies/{study_id}",
        required=False,
    )
    assert configuration_sha256((first, second)) == configuration_sha256((second, first))
    changed = replace(second, required=True)
    assert configuration_sha256((first, second)) != configuration_sha256((first, changed))
    for invalid_routes in ((), [first], (object(),)):
        with pytest.raises(CompositionContractError):
            configuration_sha256(invalid_routes)  # type: ignore[arg-type]


def test_generation_rejects_config_digest_not_derived_from_route_materialization() -> None:
    with pytest.raises(CompositionContractError, match="config_sha256"):
        CompositionGeneration(
            schema_version="orgmetra_gateway_composition.v1",
            generation_id="generation_001",
            config_sha256=C,
            routes=(route(),),
        )


def test_release_locator_requires_one_canonical_release_tag_path() -> None:
    base = release()
    for locator in (
        "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/alias/v1.2.3",
        "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3?copy=v1.2.3",
    ):
        with pytest.raises(CompositionContractError):
            replace(base, release_locator=locator)


def test_generation_rejects_overlapping_route_templates() -> None:
    parameterized = route(
        route_id="person_by_id",
        path="/v1/people/{person_record_id}",
    )
    renamed_parameter = route(
        route_id="person_by_subject",
        service_id="job_analysis_api",
        path="/v1/people/{subject_id}",
    )
    static_overlap = route(
        route_id="person_current",
        service_id="job_analysis_api",
        path="/v1/people/current",
    )
    for second in (renamed_parameter, static_overlap):
        routes = (parameterized, second)
        with pytest.raises(CompositionContractError, match="method/path authority"):
            CompositionGeneration(
                schema_version="orgmetra_gateway_composition.v1",
                generation_id="generation_001",
                config_sha256=configuration_sha256(routes),
                routes=routes,
            )


def test_generation_allows_distinct_authority_or_distinct_http_method() -> None:
    person_get = route(
        route_id="person_get",
        path="/v1/people/{person_record_id}",
    )
    job_get = route(
        route_id="job_get",
        service_id="job_analysis_api",
        path="/v1/jobs/{job_id}",
    )
    person_post = route(
        route_id="person_post",
        service_id="job_analysis_api",
        path="/v1/people/{person_record_id}",
        methods=("POST",),
    )
    routes = (person_get, job_get, person_post)
    generation = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_001",
        config_sha256=configuration_sha256(routes),
        routes=routes,
    )
    assert generation.routes == routes


def test_composition_does_not_own_retry_policy() -> None:
    assert not hasattr(route(), "retry_class")


def test_route_admission_receipt_does_not_claim_buyer_readiness() -> None:
    expected = route()
    receipt = admit_generation(generation(expected), {"people_api": expected.owner_release})
    assert not hasattr(receipt, "buyer_ready")
    assert receipt.required_routes_admitted is True


def test_admission_receipt_cannot_be_minted_outside_canonical_admission() -> None:
    with pytest.raises(CompositionContractError, match="issued only by admit_generation"):
        AdmissionReceipt(
            generation_id="generation_001",
            config_sha256=A,
            admitted_route_ids=("people_history",),
            unavailable_optional_route_ids=(),
        )

    forged = object.__new__(AdmissionReceipt)
    object.__setattr__(forged, "generation_id", "generation_001")
    object.__setattr__(forged, "config_sha256", A)
    object.__setattr__(forged, "admitted_route_ids", ("people_history",))
    object.__setattr__(forged, "unavailable_optional_route_ids", ())
    with pytest.raises(CompositionContractError, match="not canonically issued"):
        _ = forged.required_routes_admitted


def test_admission_receipt_rejects_post_issuance_field_mutation() -> None:
    expected = route()
    mutations = (
        ("generation_id", "generation_999"),
        ("config_sha256", C),
        ("admitted_route_ids", ("forged_route",)),
        ("unavailable_optional_route_ids", ("forged_optional",)),
    )
    for field, value in mutations:
        receipt = admit_generation(generation(expected), {"people_api": expected.owner_release})
        object.__setattr__(receipt, field, value)
        with pytest.raises(CompositionContractError, match="not canonically issued"):
            _ = receipt.required_routes_admitted
