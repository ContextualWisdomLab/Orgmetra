"""RFC 9457-compatible, non-leaking HTTP problem responses."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from orgmetra_postgres import (
    RepositoryAuthorizationError,
    RepositoryConflictError,
    RepositoryUnavailableError,
)
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException

from .auth import AuthenticationFailed, AuthorizationDenied, IdentityProviderUnavailable
from .support import new_support_reference

_SAFE_HTTP_RESPONSE_HEADERS = frozenset({"www-authenticate", "retry-after"})
_NEXT_ACTIONS = {
    "authentication_failed": "Obtain a valid bearer credential and retry.",
    "authorization_denied": "Request the required operation scope and business-purpose grant before retrying.",
    "repository_access_denied": "Verify the authorized tenant and repository policy before retrying.",
    "immutable_identity_conflict": "Use the existing identity facts or submit the correct versioned change.",
    "repository_unavailable": "Retry after the indicated interval; contact support if the problem persists.",
    "identity_provider_unavailable": "Retry authentication after the indicated interval.",
    "resource_not_found": "Verify the resource reference and authorized scope before retrying.",
    "request_body_too_large": "Submit a smaller request body and retry.",
    "invalid_request_metadata": "Correct the bounded request metadata and retry.",
    "request_validation_failed": "Correct the indicated request fields and retry.",
    "http_error": "Correct the HTTP request and retry.",
    "internal_error": "Contact an authorized support operator with the support reference.",
}


class ValidationIssue(BaseModel):
    """Describe one invalid field without returning the rejected value."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_path: str = Field(min_length=1, max_length=512)
    issue_code: str = Field(min_length=1, max_length=128)


class ProblemDetail(BaseModel):
    """Represent a stable Orgmetra problem detail document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=200)
    status: int = Field(ge=400, le=599)
    detail: str = Field(min_length=1, max_length=500)
    instance: str = Field(min_length=1, max_length=2048)
    error_code: str = Field(min_length=1, max_length=128)
    support_reference: str = Field(pattern=r"^err_[A-Za-z0-9_-]{20,80}$")
    next_action: str = Field(min_length=1, max_length=500)
    invalid_fields: tuple[ValidationIssue, ...] | None = None


@dataclass(frozen=True, slots=True)
class ResourceNotFound(RuntimeError):
    """Indicate that a resource is absent or deliberately undisclosed."""

    resource_type_code: str


class RequestTooLarge(RuntimeError):
    """Indicate that a request body exceeded the configured byte budget."""


class InvalidRequestMetadata(RuntimeError):
    """Indicate malformed bounded metadata such as a correlation reference."""


def register_exception_handlers(app: FastAPI) -> None:
    """Install one stable error policy for the complete application."""

    app.add_exception_handler(AuthenticationFailed, _authentication_handler)
    app.add_exception_handler(AuthorizationDenied, _authorization_handler)
    app.add_exception_handler(IdentityProviderUnavailable, _identity_provider_handler)
    app.add_exception_handler(RepositoryAuthorizationError, _repository_auth_handler)
    app.add_exception_handler(RepositoryConflictError, _conflict_handler)
    app.add_exception_handler(RepositoryUnavailableError, _unavailable_handler)
    app.add_exception_handler(ResourceNotFound, _not_found_handler)
    app.add_exception_handler(RequestTooLarge, _too_large_handler)
    app.add_exception_handler(InvalidRequestMetadata, _metadata_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unexpected_handler)


async def _authentication_handler(
    request: Request, _error: AuthenticationFailed
) -> JSONResponse:
    """Return a fixed authentication response without token details."""

    return _response(
        request,
        status_code=401,
        error_code="authentication_failed",
        title="Authentication required",
        detail="Valid bearer authentication is required for this operation.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _authorization_handler(
    request: Request, _error: AuthorizationDenied
) -> JSONResponse:
    """Return a fixed denial without disclosing which authority was absent."""

    return _response(
        request,
        status_code=403,
        error_code="authorization_denied",
        title="Authorization denied",
        detail="The authenticated principal is not authorized for this operation.",
    )


async def _identity_provider_handler(
    request: Request, _error: IdentityProviderUnavailable
) -> JSONResponse:
    """Return a fixed retryable identity-provider outage response."""

    return _response(
        request,
        status_code=503,
        error_code="identity_provider_unavailable",
        title="Identity provider unavailable",
        detail="Authentication services are temporarily unavailable.",
        headers={"Retry-After": "5"},
    )


async def _repository_auth_handler(
    request: Request, _error: RepositoryAuthorizationError
) -> JSONResponse:
    """Return a fixed database-boundary authorization denial."""

    return _response(
        request,
        status_code=403,
        error_code="repository_access_denied",
        title="Repository access denied",
        detail="The requested data operation is not authorized.",
    )


async def _conflict_handler(
    request: Request, _error: RepositoryConflictError
) -> JSONResponse:
    """Return an identity conflict without exposing existing HR facts."""

    return _response(
        request,
        status_code=409,
        error_code="immutable_identity_conflict",
        title="Immutable identity conflict",
        detail="The requested identity conflicts with an existing record.",
    )


async def _unavailable_handler(
    request: Request, _error: RepositoryUnavailableError
) -> JSONResponse:
    """Return a retryable dependency failure without infrastructure details."""

    return _response(
        request,
        status_code=503,
        error_code="repository_unavailable",
        title="Repository unavailable",
        detail="The data service is temporarily unavailable.",
        headers={"Retry-After": "5"},
    )


async def _not_found_handler(
    request: Request, _error: ResourceNotFound
) -> JSONResponse:
    """Return a uniform not-found response to avoid existence disclosure."""

    return _response(
        request,
        status_code=404,
        error_code="resource_not_found",
        title="Resource not found",
        detail="The requested resource does not exist or is not visible.",
    )


async def _too_large_handler(
    request: Request, _error: RequestTooLarge
) -> JSONResponse:
    """Return a fixed request-size refusal."""

    return _response(
        request,
        status_code=413,
        error_code="request_body_too_large",
        title="Request body too large",
        detail="The request body exceeds the configured byte limit.",
    )


async def _metadata_handler(
    request: Request, _error: InvalidRequestMetadata
) -> JSONResponse:
    """Return a fixed malformed metadata response."""

    return _response(
        request,
        status_code=400,
        error_code="invalid_request_metadata",
        title="Invalid request metadata",
        detail="One or more bounded request metadata fields are invalid.",
    )


async def _validation_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Return field locations and error types without rejected values."""

    issues = tuple(
        ValidationIssue(
            field_path=".".join(str(part) for part in item.get("loc", ("request",))),
            issue_code=str(item.get("type", "invalid_value"))[:128],
        )
        for item in error.errors()
    )
    return _response(
        request,
        status_code=422,
        error_code="request_validation_failed",
        title="Request validation failed",
        detail="The request does not satisfy the published schema.",
        invalid_fields=issues,
    )


async def _http_exception_handler(
    request: Request, error: HTTPException
) -> JSONResponse:
    """Normalize framework HTTP failures and preserve only safe response headers."""

    safe_headers = {
        name: value
        for name, value in (error.headers or {}).items()
        if name.casefold() in _SAFE_HTTP_RESPONSE_HEADERS
    }
    return _response(
        request,
        status_code=error.status_code,
        error_code="http_error",
        title="HTTP request failed",
        detail="The HTTP request could not be completed.",
        headers=safe_headers or None,
    )


async def _unexpected_handler(request: Request, _error: Exception) -> JSONResponse:
    """Return a fixed internal failure without exception or content leakage."""

    return _response(
        request,
        status_code=500,
        error_code="internal_error",
        title="Internal server error",
        detail="The service could not complete the request.",
    )


def _response(
    request: Request,
    *,
    status_code: int,
    error_code: str,
    title: str,
    detail: str,
    invalid_fields: tuple[ValidationIssue, ...] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build one canonical problem response with a client-safe support reference."""

    support_reference = getattr(
        request.state,
        "support_reference",
        new_support_reference(),
    )
    document = ProblemDetail(
        type=f"urn:orgmetra:problem:{error_code}",
        title=title,
        status=status_code,
        detail=detail,
        instance=request.url.path,
        error_code=error_code,
        support_reference=support_reference,
        next_action=_NEXT_ACTIONS.get(
            error_code,
            "Correct the request or contact support with the support reference.",
        ),
        invalid_fields=invalid_fields,
    )
    response_headers = {
        "Cache-Control": "no-store",
        "X-Support-Reference": support_reference,
    }
    if headers is not None:
        response_headers.update(headers)
    return JSONResponse(
        status_code=status_code,
        content=document.model_dump(mode="json", exclude_none=True),
        media_type="application/problem+json",
        headers=response_headers,
    )
