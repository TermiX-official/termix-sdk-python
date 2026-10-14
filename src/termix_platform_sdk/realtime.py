"""Realtime via Centrifugo SSE (no webhooks). Parses text/event-stream over httpx."""
from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Optional

import httpx


def _parse_event(raw: str) -> Optional[dict]:
    event: Optional[str] = None
    _id: Optional[str] = None
    data: list = []
    for line in raw.split("\n"):
        if line.startswith(":"):
            continue
        field, _, val = line.partition(":")
        val = val[1:] if val.startswith(" ") else val
        if field == "event":
            event = val
        elif field == "id":
            _id = val
        elif field == "data":
            data.append(val)
    if not data and not event:
        return None
    return {"event": event, "id": _id, "data": "\n".join(data)}


class RealtimeResource:
    def __init__(self, base_url: str, token_provider: Callable[[], Optional[str]], client: Optional[httpx.AsyncClient] = None) -> None:
        self._base = base_url.rstrip("/")
        self._tp = token_provider
        self._client = client

    async def subscribe(
        self, on_event: Callable[[dict], Any], on_error: Optional[Callable[[Exception], Any]] = None
    ) -> asyncio.Task:
        """Returns an asyncio.Task; cancel it to stop the subscription."""
        token = self._tp()
        if not token:
            raise RuntimeError("realtime.subscribe requires an authenticated session (no token)")
        url = f"{self._base}/realtime/sse?token={token}"

        async def run() -> None:
            client = self._client or httpx.AsyncClient(timeout=None)
            try:
                async with client.stream("GET", url, headers={"accept": "text/event-stream"}) as resp:
                    if resp.status_code >= 400:
                        raise RuntimeError(f"realtime SSE failed: HTTP {resp.status_code}")
                    buf = ""
                    async for chunk in resp.aiter_text():
                        buf += chunk
                        while "\n\n" in buf:
                            raw, buf = buf.split("\n\n", 1)
                            ev = _parse_event(raw)
                            if ev:
                                res = on_event(ev)
                                if inspect.isawaitable(res):
                                    await res
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                if on_error:
                    res = on_error(e)
                    if inspect.isawaitable(res):
                        await res
            finally:
                if self._client is None:
                    await client.aclose()

        return asyncio.create_task(run())
