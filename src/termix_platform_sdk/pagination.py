"""Pagination helpers mirroring the backend `{items,page,pageSize,total,totalPages}`."""
from __future__ import annotations

from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List


async def paginate(fetch_page: Callable[[int], Awaitable[Dict[str, Any]]], start_page: int = 1) -> AsyncIterator[Any]:
    page = start_page
    while True:
        res = await fetch_page(page)
        items = res.get("items") or []
        for item in items:
            yield item
        if not items or page >= (res.get("totalPages") or page):
            break
        page += 1


async def collect(gen: AsyncIterator[Any], limit: int = 2**31) -> List[Any]:
    out: List[Any] = []
    async for item in gen:
        out.append(item)
        if len(out) >= limit:
            break
    return out
