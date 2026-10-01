"""Reject module-exposed capabilities that can mint authorized public views."""

from __future__ import annotations

from inspect import getmodule
from uuid import UUID

import pytest

import orgmetra_workforce_validation_api as api
from orgmetra_workforce_validation_api import registry


TENANT = UUID("11111111-1111-4111-8111-111111111111")
STUDY = UUID("22222222-2222-4222-8222-222222222222")


def test_public_authorized_view_modules_expose_no_issuance_marker_capability() -> None:
    """Keep view-sealing write capabilities out of ordinary module state."""
    for name in sorted(item for item in api.__all__ if item.endswith("View")):
        view_type = getattr(api, name)
        module = getmodule(view_type)
        assert module is not None
        exposed = tuple(
            sorted(key for key in vars(module) if key.endswith("_ISSUANCE_MARKER"))
        )
        assert exposed == (), f"{name} owner module exposes issuance markers: {exposed!r}"


def test_registry_module_marker_cannot_mint_authorized_projection() -> None:
    """Reject a raw view whose caller fills slots with any importable marker-like value."""
    forged = object.__new__(registry.ValidityStudyView)
    object.__setattr__(forged, "_tenant_identity", TENANT.int)
    object.__setattr__(forged, "_study_identity", STUDY.int)
    object.__setattr__(
        forged,
        "_fields",
        (("study_status_code", "study_closed"),),
    )
    caller_marker = getattr(
        registry,
        "_VALIDITY_STUDY_VIEW_ISSUANCE_MARKER",
        object(),
    )
    object.__setattr__(forged, "_issuance_marker", caller_marker)

    with pytest.raises(
        registry.ValidityStudyIntegrityError,
        match="was not issued by read_validity_study",
    ):
        _ = forged.fields
