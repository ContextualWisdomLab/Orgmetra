from __future__ import annotations

import pytest

from orgmetra_product_composition import CompositionContractError, OwnerApiRelease

A = "a" * 64
B = "b" * 64


def release_locator(repository: str) -> str:
    return f"https://github.com/ContextualWisdomLab/{repository}/releases/tag/v1.2.3"


def test_owner_release_rejects_foreign_cwl_repository_coordinate() -> None:
    with pytest.raises(CompositionContractError, match="Orgmetra release repository"):
        OwnerApiRelease(
            service_id="people_api",
            release_version="v1.2.3",
            openapi_sha256=A,
            artifact_sha256=B,
            release_locator=release_locator("TEPP"),
        )


def test_owner_release_accepts_orgmetra_repository_coordinate() -> None:
    owner = OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256=A,
        artifact_sha256=B,
        release_locator=release_locator("Orgmetra"),
    )

    assert owner.release_locator == release_locator("Orgmetra")
