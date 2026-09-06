"""Tenant identity interoperability regressions for compensation-change review evidence."""

import pytest

from orgmetra_compensation_change_review import build_compensation_change_review_packet


_AUTHORITATIVE_UUIDV7_TENANT = "10000000-0000-7000-8000-000000000001"


def _build_with_tenant(tenant_record_id: str, valid_packet_kwargs: dict[str, object]):
    """Build a valid value-minimized compensation packet around one tenant identity."""
    kwargs = valid_packet_kwargs.copy()
    kwargs["tenant_record_id"] = tenant_record_id
    return build_compensation_change_review_packet(**kwargs)


def test_accepts_authoritative_operational_uuidv7_tenant_identity(
    valid_packet_kwargs: dict[str, object],
) -> None:
    """Accept the canonical UUIDv7 tenant form already accepted by protected HRIS core."""
    packet = _build_with_tenant(_AUTHORITATIVE_UUIDV7_TENANT, valid_packet_kwargs)
    assert packet.tenant_record_id == _AUTHORITATIVE_UUIDV7_TENANT


@pytest.mark.parametrize(
    "tenant_record_id",
    [
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
    ],
)
def test_rejects_reserved_sentinel_tenant_identity(
    tenant_record_id: str,
    valid_packet_kwargs: dict[str, object],
) -> None:
    """Reject RFC 9562 Nil/Max sentinels while deferring UUID version policy to HRIS core."""
    with pytest.raises(ValueError, match="tenant_record_id"):
        _build_with_tenant(tenant_record_id, valid_packet_kwargs)
