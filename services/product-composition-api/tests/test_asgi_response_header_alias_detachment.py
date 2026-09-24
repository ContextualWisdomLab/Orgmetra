from __future__ import annotations

import asyncio

from orgmetra_product_composition.asgi_response_send import send_complete_http_response


def test_complete_response_detaches_mutable_header_pairs_before_transport() -> None:
    """Do not let caller-held header containers rewrite a prevalidated response during send."""

    caller_headers = [[b"content-type", b"text/plain"]]
    first_send_started = asyncio.Event()
    release_first_send = asyncio.Event()
    observed: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        if message["type"] == "http.response.start":
            first_send_started.set()
            await release_first_send.wait()
        observed.append(message)

    async def scenario() -> None:
        response_task = asyncio.create_task(
            send_complete_http_response(
                send,
                status=200,
                headers=caller_headers,
                body=b"ok",
            )
        )
        await first_send_started.wait()
        caller_headers[0][0] = b"bad name"
        caller_headers[0][1] = b"bad\r\nvalue"
        release_first_send.set()
        await response_task

    asyncio.run(scenario())

    assert observed[0] == {
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"text/plain")],
    }
    assert observed[1] == {
        "type": "http.response.body",
        "body": b"ok",
        "more_body": False,
    }
