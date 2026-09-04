"""Public contracts for governed Orgmetra HR document retrieval."""

from .retrieval import (
    DocumentArtifact,
    DocumentArtifactReader,
    DocumentMetadataResolver,
    DocumentRetrievalAuthorization,
    DocumentRetrievalAuthority,
    DocumentRetrievalQuery,
    DocumentRetrievalResult,
    DocumentRetrievalScope,
    HrDocumentRetrievalError,
    ImmutableRetrievalAuditWriter,
    retrieve_hr_document,
)

__all__ = [
    "DocumentArtifact",
    "DocumentArtifactReader",
    "DocumentMetadataResolver",
    "DocumentRetrievalAuthority",
    "DocumentRetrievalAuthorization",
    "DocumentRetrievalQuery",
    "DocumentRetrievalResult",
    "DocumentRetrievalScope",
    "HrDocumentRetrievalError",
    "ImmutableRetrievalAuditWriter",
    "retrieve_hr_document",
]
