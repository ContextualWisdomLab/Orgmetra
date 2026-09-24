from __future__ import annotations

import asyncio

import pytest

from orgmetra_product_composition.asgi_response_send import (
    CompositionResponseEventError,
    send_complete_http_response,
)


def test_complete_response_rejects_application_transfer_encoding_before_transport() -> None:
    """Keep response transfer-coding authority with the ASGI protocol server."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="transfer-encoding"):
        asyncio.run(
            send_complete_http_response(
                send,
                status=200,
                headers=((b"transfer-encoding", b"chunked"),),
                body=b"payload",
            )
        )

    assert calls == 0


def test_complete_response_rejects_mixed_transfer_encoding_and_content_length() -> None:
    """Reject ambiguous application framing before either response event reaches transport."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="transfer-encoding"):
        asyncio.run(
            send_complete_http_response(
                send,
                status=200,
                headers=(
                    (b"transfer-encoding", b"chunked"),
                    (b"content-length", b"7"),
                ),
                body=b"payload",
            )
        )

    assert calls == 0
