from __future__ import annotations

import asyncio

import pytest

from orgmetra_product_composition.asgi_response_send import (
    CompositionResponseEventError,
    send_complete_http_response,
)


def test_complete_response_prevalidates_entire_message_before_transport() -> None:
    """Reject an invalid terminal body before response-start makes the response irreversible."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="response.body"):
        asyncio.run(
            send_complete_http_response(
                send,
                status=200,
                headers=((b"content-type", b"application/json"),),
                body="not-bytes",
            )
        )

    assert calls == 0


def test_complete_response_rejects_informational_status_as_final_response() -> None:
    """Keep informational status handling out of the terminal core-response completion path."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="final response status"):
        asyncio.run(
            send_complete_http_response(
                send,
                status=103,
                headers=(),
                body=b"",
            )
        )

    assert calls == 0


def test_complete_response_rejects_invalid_headers_before_transport() -> None:
    """Prevalidate response-start metadata before any irreversible send is attempted."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="response.start headers"):
        asyncio.run(
            send_complete_http_response(
                send,
                status=200,
                headers="not-headers",
                body=b"ok",
            )
        )

    assert calls == 0


def test_complete_response_sends_start_then_one_terminal_body() -> None:
    """Emit exactly one response-start followed by one terminal response-body event."""

    events: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        events.append(message)

    asyncio.run(
        send_complete_http_response(
            send,
            status=200,
            headers=((b"content-type", b"application/json"),),
            body=b'{"ok":true}',
        )
    )

    assert events == [
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        },
        {
            "type": "http.response.body",
            "body": b'{"ok":true}',
            "more_body": False,
        },
    ]


def test_complete_response_can_suppress_content_without_changing_metadata() -> None:
    """Support HEAD-style content suppression while preserving the response-start metadata."""

    events: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        events.append(message)

    asyncio.run(
        send_complete_http_response(
            send,
            status=404,
            headers=((b"content-type", b"application/problem+json"),),
            body=b'{"type":"about:blank"}',
            suppress_body=True,
        )
    )

    assert events[0] == {
        "type": "http.response.start",
        "status": 404,
        "headers": [(b"content-type", b"application/problem+json")],
    }
    assert events[1] == {
        "type": "http.response.body",
        "body": b"",
        "more_body": False,
    }


@pytest.mark.parametrize("status", [204, 205, 304])
def test_complete_response_suppresses_status_forbidden_content(status: int) -> None:
    """Do not put representation bytes on the wire when HTTP status semantics forbid content."""

    events: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        events.append(message)

    asyncio.run(
        send_complete_http_response(
            send,
            status=status,
            headers=(),
            body=b"representation bytes",
        )
    )

    assert events == [
        {"type": "http.response.start", "status": status, "headers": []},
        {"type": "http.response.body", "body": b"", "more_body": False},
    ]


def test_complete_response_rejects_content_length_on_204_before_transport() -> None:
    """Enforce the RFC 9110 prohibition on Content-Length in a 204 response."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="204.*content-length"):
        asyncio.run(
            send_complete_http_response(
                send,
                status=204,
                headers=((b"content-length", b"0"),),
                body=b"",
            )
        )

    assert calls == 0


@pytest.mark.parametrize(
    ("status", "suppress_body", "body", "content_length"),
    [
        (200, False, b"abc", b"2"),
        (200, False, b"abc", b"x"),
        (200, False, b"abc", b"3, 3"),
        (200, True, b"abc", b"2"),
        (304, False, b"abc", b"2"),
        (205, False, b"abc", b"3"),
    ],
)
def test_complete_response_rejects_inconsistent_content_length_before_transport(
    status: int,
    suppress_body: bool,
    body: bytes,
    content_length: bytes,
) -> None:
    """Fail closed when explicit Content-Length disagrees with the owned response semantics."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="content-length"):
        asyncio.run(
            send_complete_http_response(
                send,
                status=status,
                headers=((b"content-length", content_length),),
                body=body,
                suppress_body=suppress_body,
            )
        )

    assert calls == 0


@pytest.mark.parametrize(
    ("status", "suppress_body", "body", "content_length"),
    [
        (200, False, b"abc", b"3"),
        (200, True, b"abc", b"3"),
        (304, False, b"abc", b"3"),
        (205, False, b"abc", b"0"),
    ],
)
def test_complete_response_accepts_consistent_content_length(
    status: int,
    suppress_body: bool,
    body: bytes,
    content_length: bytes,
) -> None:
    """Allow one canonical Content-Length when it matches representation or no-content semantics."""

    events: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        events.append(message)

    asyncio.run(
        send_complete_http_response(
            send,
            status=status,
            headers=((b"content-length", content_length),),
            body=body,
            suppress_body=suppress_body,
        )
    )

    expected_wire_body = b"" if suppress_body or status in {205, 304} else body
    assert events[0]["headers"] == [(b"content-length", content_length)]
    assert events[1]["body"] == expected_wire_body


def test_complete_response_rejects_duplicate_content_length_before_transport() -> None:
    """Reject ambiguous duplicate Content-Length rather than normalize framing authority locally."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="content-length"):
        asyncio.run(
            send_complete_http_response(
                send,
                status=200,
                headers=((b"content-length", b"3"), (b"content-length", b"3")),
                body=b"abc",
            )
        )

    assert calls == 0


def test_complete_response_rejects_non_boolean_suppression_before_transport() -> None:
    """Reject truthy lookalikes instead of letting caller state alter body semantics implicitly."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="suppress_body"):
        asyncio.run(
            send_complete_http_response(
                send,
                status=200,
                headers=(),
                body=b"ok",
                suppress_body=1,
            )
        )

    assert calls == 0


def test_complete_response_does_not_attempt_body_after_start_failure() -> None:
    """Preserve the first server failure and do not continue a response whose start did not send."""

    failure = BrokenPipeError("connection closed before response start")
    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1
        raise failure

    with pytest.raises(BrokenPipeError) as caught:
        asyncio.run(
            send_complete_http_response(
                send,
                status=503,
                headers=(),
                body=b"unavailable",
            )
        )

    assert caught.value is failure
    assert calls == 1


def test_complete_response_preserves_terminal_body_send_failure() -> None:
    """Expose a post-start transport failure without retrying or remapping the partial response."""

    failure = ConnectionResetError("connection closed during body send")
    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise failure

    with pytest.raises(ConnectionResetError) as caught:
        asyncio.run(
            send_complete_http_response(
                send,
                status=200,
                headers=(),
                body=b"ok",
            )
        )

    assert caught.value is failure
    assert calls == 2
