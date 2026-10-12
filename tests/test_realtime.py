from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from termix_platform_sdk.realtime import RealtimeResource


class ChunkedStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk


@pytest.mark.asyncio
async def test_subscribe_parses_all_sse_line_endings_and_encodes_token() -> None:
    token = "session+token&scope=realtime"
    events: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["token"] == token
        assert request.url.query == b"token=session%2Btoken%26scope%3Drealtime"
        assert all(value is None for value in request.extensions["timeout"].values())
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=ChunkedStream(
                [
                    b"event: first\r",
                    b"\nid: 7\r\ndata: ready\r\n\r",
                    b"\nevent: second\rdata: next\r\r",
                ]
            ),
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        timeout=0.001,
    ) as client:
        realtime = RealtimeResource(
            "https://example.test/api/v1",
            lambda: token,
            client=client,
        )
        task = await realtime.subscribe(events.append)
        await task

    assert events == [
        {"event": "first", "id": "7", "data": "ready"},
        {"event": "second", "id": None, "data": "next"},
    ]
