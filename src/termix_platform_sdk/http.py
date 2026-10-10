"""Async HTTP client: idempotency-aware retry, 401 auto-refresh, typed errors,
interceptors, header redaction."""
from __future__ import annotations

import asyncio
import json
import random
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

from .errors import NetworkError, map_api_error

_SENSITIVE = {"authorization", "idempotency-key"}


def _redact(headers: Dict[str, str]) -> Dict[str, str]:
    return {k: ("<redacted>" if k.lower() in _SENSITIVE else v) for k, v in headers.items()}


def _clean_query(query: Optional[dict]) -> Optional[dict]:
    if not query:
        return None
    out: Dict[str, Any] = {}
    for k, v in query.items():
        if v is None:
            continue
        out[k] = "true" if v is True else "false" if v is False else v
    return out


class HttpClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_s: float = 30.0,
        max_retries: int = 2,
        token_provider: Optional[Callable[[], Optional[str]]] = None,
        on_unauthorized: Optional[Callable[[], Awaitable[bool]]] = None,
        interceptors: Optional[List[dict]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.token_provider = token_provider
        self.on_unauthorized = on_unauthorized
        self.interceptors = interceptors or []
        self._client = client or httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _url(self, path: str) -> str:
        return self.base_url + (path if path.startswith("/") else f"/{path}")

    async def _backoff(self, attempt: int) -> None:
        await asyncio.sleep(min(1.0 * 2 ** (attempt - 1), 8.0) + random.random() * 0.25)

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[dict] = None,
        body: Any = None,
        headers: Optional[dict] = None,
        idempotent: bool = False,
        auth: bool = True,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        max_retries = self.max_retries if idempotent else 0
        attempt = 0
        refreshed = False
        while True:
            h: Dict[str, str] = {"accept": "application/json", **(headers or {})}
            if body is not None:
                h["content-type"] = "application/json"
            if idempotency_key:
                h["idempotency-key"] = idempotency_key
            if auth and self.token_provider:
                tok = self.token_provider()
                if tok:
                    h["authorization"] = f"Bearer {tok}"
            for itc in self.interceptors:
                if itc.get("on_request"):
                    itc["on_request"]({"method": method, "url": self._url(path), "headers": _redact(h)})
            try:
                resp = await self._client.request(
                    method,
                    self._url(path),
                    params=_clean_query(query),
                    content=json.dumps(body) if body is not None else None,
                    headers=h,
                )
            except httpx.TimeoutException as e:
                if attempt < max_retries:
                    attempt += 1
                    await self._backoff(attempt)
                    continue
                raise NetworkError(f"request timeout: {method} {path}") from e
            except httpx.HTTPError as e:
                if attempt < max_retries:
                    attempt += 1
                    await self._backoff(attempt)
                    continue
                raise NetworkError(f"network error: {method} {path}") from e

            for itc in self.interceptors:
                if itc.get("on_response"):
                    itc["on_response"]({"method": method, "url": self._url(path), "status": resp.status_code})

            if resp.status_code == 401 and auth and not refreshed and self.on_unauthorized:
                refreshed = await self.on_unauthorized()
                if refreshed:
                    continue

            data: Any = None
            if resp.status_code != 204 and resp.content:
                try:
                    data = resp.json()
                except ValueError:
                    data = resp.text

            if resp.status_code >= 400:
                if (resp.status_code >= 500 or resp.status_code == 429) and attempt < max_retries:
                    attempt += 1
                    await self._backoff(attempt)
                    continue
                raise map_api_error(resp.status_code, data)
            return data

    async def get(self, path: str, **kw: Any) -> Any:
        kw.setdefault("idempotent", True)
        return await self.request("GET", path, **kw)

    async def post(self, path: str, **kw: Any) -> Any:
        return await self.request("POST", path, **kw)

    async def patch(self, path: str, **kw: Any) -> Any:
        return await self.request("PATCH", path, **kw)

    async def delete(self, path: str, **kw: Any) -> Any:
        kw.setdefault("idempotent", True)
        return await self.request("DELETE", path, **kw)
