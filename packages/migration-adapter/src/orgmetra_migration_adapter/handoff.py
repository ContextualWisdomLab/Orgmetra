"""Governed, value-free migration handoff evidence for Orgmetra.

This module owns only Orgmetra's pre-write governance envelope. It does not parse
MHTML, transform source values, call mightyETL, hold credentials, or write HRIS
tables. Those responsibilities remain behind their published owner contracts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Final
from uuid import UUID


MHTML_ETL_GATEWAY_REVISION: Final = "779254927abb1e7cee80fd949907ccd03f9fc7be"
MIGHTY_ETL_REVISION: Final = "ba8911f50ed20a39927a0d51c0cf20f9b7c91820"
MIGRATION_CONTRACT_VERSION: Final = "orgmetra.migration_handoff.v1"
MAXIMUM_BATCH_RECORDS: Final = 1000

_ALLOWED_TARGET_OBJECT_CODES: Final = frozenset(
    {
        "assignment_record",
        "employment_record",
        "job_profile",
        "organization_unit",
        "person_record",
        "position_record",
    }
)
_SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA_PROPOSAL_PATTERN: Final = re.compile(r"^schema_proposal_[0-9a-f]{32}$")
_CODE_PATTERN: Final = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_REFERENCE_PATTERN: Final = re.compile(
    r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]{0,199}$"
)


class ContractViolation(ValueError):
    """Raised when migration evidence cannot satisfy the fail-closed contract."""


@dataclass(frozen=True, slots=True)
class MigrationHandoffInput:
    """Caller-supplied value-free evidence required before one HRIS import batch.

    The type deliberately has no raw header, source value, credential, or
    destination connection field. Source inspection and transformation stay in
    their dedicated owner services.
    """

    tenant_record_id: str
    migration_batch_reference: str
    actor_reference: str
    approval_reference: str
    purpose_code: str
    reason_code: str
    human_confirmed: bool
    source_sha256: str
    source_size_bytes: int
    schema_proposal_id: str
    table_fingerprint_sha256: str
    mapping_digest_sha256: str
    record_count: int
    target_object_codes: tuple[str, ...]
    mhtml_contract_revision: str = MHTML_ETL_GATEWAY_REVISION
    mightyetl_contract_revision: str = MIGHTY_ETL_REVISION


@dataclass(frozen=True, slots=True)
class MigrationHandoffEnvelope:
    """Canonical, PII-minimized evidence that a bounded migration may proceed."""

    contract_version: str
    tenant_record_id: str
    migration_batch_reference: str
    actor_reference: str
    approval_reference: str
    purpose_code: str
    reason_code: str
    source_sha256: str
    source_size_bytes: int
    schema_proposal_id: str
    table_fingerprint_sha256: str
    mapping_digest_sha256: str
    record_count: int
    target_object_codes: tuple[str, ...]
    mhtml_contract_revision: str
    mightyetl_contract_revision: str
    privacy_mode: str
    execution_mode: str
    requires_reconciliation: bool
    next_action: str

    def __post_init__(self) -> None:
        """Reject direct construction that would produce noncanonical evidence."""
        if self.contract_version != MIGRATION_CONTRACT_VERSION:
            raise ContractViolation("migration envelope contract version is unsupported")
        if self.target_object_codes != tuple(sorted(set(self.target_object_codes))):
            raise ContractViolation("migration target objects must be sorted and unique")
        if self.privacy_mode != "value_free":
            raise ContractViolation("migration envelope privacy mode must remain value_free")
        if self.execution_mode != "bounded_atomic_batch":
            raise ContractViolation("migration envelope execution mode is unsupported")
        if self.requires_reconciliation is not True:
            raise ContractViolation("migration completion requires explicit reconciliation")
        if not self.next_action:
            raise ContractViolation("migration envelope must provide a next action")

    def to_dict(self) -> dict[str, object]:
        """Return the deterministic JSON-ready representation."""
        payload = asdict(self)
        payload["target_object_codes"] = list(self.target_object_codes)
        return payload

    def canonical_json(self) -> str:
        """Return deterministic UTF-8 JSON used for immutable audit correlation."""
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def digest_sha256(self) -> str:
        """Address the exact canonical envelope without copying source values."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_migration_handoff(
    evidence: MigrationHandoffInput,
) -> MigrationHandoffEnvelope:
    """Validate value-free owner evidence and build one bounded migration envelope.

    Raises:
        ContractViolation: Any governance, identity, provenance, dependency
            revision, or bounded-batch invariant is not satisfied.
    """
    _require_operational_uuid(evidence.tenant_record_id)
    _require_reference(evidence.migration_batch_reference, "migration batch reference")
    _require_reference(evidence.actor_reference, "actor reference")
    _require_reference(evidence.approval_reference, "approval reference")
    _require_code(evidence.purpose_code, "purpose code")
    if evidence.purpose_code != "hris_data_migration":
        raise ContractViolation("migration purpose must be hris_data_migration")
    _require_code(evidence.reason_code, "reason code")
    if evidence.human_confirmed is not True:
        raise ContractViolation("migration handoff requires explicit human confirmation")
    _require_sha256(evidence.source_sha256, "source digest")
    _require_positive_int(evidence.source_size_bytes, "source size")
    if not _SCHEMA_PROPOSAL_PATTERN.fullmatch(evidence.schema_proposal_id):
        raise ContractViolation("schema proposal identifier is malformed")
    _require_sha256(evidence.table_fingerprint_sha256, "table fingerprint")
    _require_sha256(evidence.mapping_digest_sha256, "mapping digest")
    _require_positive_int(evidence.record_count, "record count")
    if evidence.record_count > MAXIMUM_BATCH_RECORDS:
        raise ContractViolation("migration batch exceeds the reviewed record bound")
    target_object_codes = _canonical_target_objects(evidence.target_object_codes)
    if evidence.mhtml_contract_revision != MHTML_ETL_GATEWAY_REVISION:
        raise ContractViolation("MHTML ETL Gateway contract revision requires revalidation")
    if evidence.mightyetl_contract_revision != MIGHTY_ETL_REVISION:
        raise ContractViolation("mightyETL contract revision requires revalidation")

    return MigrationHandoffEnvelope(
        contract_version=MIGRATION_CONTRACT_VERSION,
        tenant_record_id=evidence.tenant_record_id,
        migration_batch_reference=evidence.migration_batch_reference,
        actor_reference=evidence.actor_reference,
        approval_reference=evidence.approval_reference,
        purpose_code=evidence.purpose_code,
        reason_code=evidence.reason_code,
        source_sha256=evidence.source_sha256,
        source_size_bytes=evidence.source_size_bytes,
        schema_proposal_id=evidence.schema_proposal_id,
        table_fingerprint_sha256=evidence.table_fingerprint_sha256,
        mapping_digest_sha256=evidence.mapping_digest_sha256,
        record_count=evidence.record_count,
        target_object_codes=target_object_codes,
        mhtml_contract_revision=evidence.mhtml_contract_revision,
        mightyetl_contract_revision=evidence.mightyetl_contract_revision,
        privacy_mode="value_free",
        execution_mode="bounded_atomic_batch",
        requires_reconciliation=True,
        next_action=(
            "Submit this approved bounded batch through the configured mightyETL "
            "adapter, then reconcile its outcome before marking the migration complete."
        ),
    )


def _require_operational_uuid(value: str) -> None:
    try:
        parsed = UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ContractViolation("tenant record identifier is malformed") from exc
    if parsed.int in (0, (1 << 128) - 1):
        raise ContractViolation("tenant record identifier uses a reserved UUID sentinel")


def _require_reference(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REFERENCE_PATTERN.fullmatch(value):
        raise ContractViolation(f"{label} is malformed")


def _require_code(value: str, label: str) -> None:
    if not isinstance(value, str) or not _CODE_PATTERN.fullmatch(value):
        raise ContractViolation(f"{label} is malformed")


def _require_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ContractViolation(f"{label} must be lowercase SHA-256")


def _require_positive_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ContractViolation(f"{label} must be a positive integer")


def _canonical_target_objects(values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise ContractViolation("migration target objects must be a non-empty tuple")
    if any(not isinstance(value, str) for value in values):
        raise ContractViolation("migration target object code is malformed")
    if len(set(values)) != len(values):
        raise ContractViolation("migration target objects must be unique")
    if any(value not in _ALLOWED_TARGET_OBJECT_CODES for value in values):
        raise ContractViolation("migration target object is outside the HRIS core")
    return tuple(sorted(values))
