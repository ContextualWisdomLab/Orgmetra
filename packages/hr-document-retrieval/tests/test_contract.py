"""Contract-first regression for purpose-bound HR document retrieval."""

from hashlib import sha256


def test_public_document_retrieval_contract_exists() -> None:
    """The buyer-visible execution boundary must exist before this test can pass."""
    from orgmetra_hr_document_retrieval import (
        DocumentArtifact,
        DocumentRetrievalAuthorization,
        DocumentRetrievalQuery,
        DocumentRetrievalResult,
        DocumentRetrievalScope,
        HrDocumentRetrievalError,
        retrieve_hr_document,
    )

    assert DocumentArtifact is not None
    assert DocumentRetrievalAuthorization is not None
    assert DocumentRetrievalQuery is not None
    assert DocumentRetrievalResult is not None
    assert DocumentRetrievalScope is not None
    assert HrDocumentRetrievalError is not None
    assert callable(retrieve_hr_document)
    assert sha256(b"contract").hexdigest()
