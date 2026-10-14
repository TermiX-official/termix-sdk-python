import asyncio

import httpx
import pytest

from termix_platform_sdk.realtime import RealtimeResource, _parse_event


def test_parse_event_basic():
    raw = "event: message\nid: 123\ndata: hello world"
    ev = _parse_event(raw)
    assert ev == {"event": "message", "id": "123", "data": "hello world"}


def test_parse_event_multiline_data():
    raw = "event: update\ndata: line 1\ndata: line 2"
    ev = _parse_event(raw)
    assert ev == {"event": "update", "id": None, "data": "line 1\nline 2"}


def test_parse_event_ignores_comments():
    raw = ": comment line\nevent: ping\ndata: pong"
    ev = _parse_event(raw)
    assert ev == {"event": "ping", "id": None, "data": "pong"}


def test_parse_event_empty():
    assert _parse_event("") is None
    assert _parse_event(": just comment") is None


@pytest.mark.asyncio
async def test_subscribe_sync_and_async_handlers():
    sse_body = b"event: msg\ndata: chunk1\n\nevent: msg\ndata: chunk2\n\n"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse_body, headers={"content-type": "text/event-stream"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    events_received = []

    async def async_on_event(ev):
        await asyncio.sleep(0.001)
        events_received.append(ev["data"])

    res = RealtimeResource("https://api.test", lambda: "mock-token", client=client)
    task = await res.subscribe(async_on_event)
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await client.aclose()

    assert events_received == ["chunk1", "chunk2"]


@pytest.mark.asyncio
async def test_subscribe_async_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"Server error")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    errors = []

    async def async_on_error(err):
        await asyncio.sleep(0.001)
        errors.append(str(err))

    res = RealtimeResource("https://api.test", lambda: "mock-token", client=client)
    await res.subscribe(lambda ev: None, on_error=async_on_error)
    await asyncio.sleep(0.05)
    await client.aclose()

    assert len(errors) == 1
    assert "realtime SSE failed: HTTP 500" in errors[0]
