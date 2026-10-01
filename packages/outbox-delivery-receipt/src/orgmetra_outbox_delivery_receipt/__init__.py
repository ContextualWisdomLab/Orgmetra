"""Public contract for Orgmetra external outbox delivery receipt evidence."""

from .receipt import (
    ExternalDeliveryReceiptEvidence,
    build_external_delivery_receipt_evidence,
    verify_exact_delivery_attempt,
)

__all__ = [
    "ExternalDeliveryReceiptEvidence",
    "build_external_delivery_receipt_evidence",
    "verify_exact_delivery_attempt",
]
