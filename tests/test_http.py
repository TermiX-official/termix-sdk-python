import httpx
import pytest

from termix_platform_sdk.auth import AuthResource, TokenStore
from termix_platform_sdk.errors import ConflictError, NotFoundError, ValidationError
from termix_platform_sdk.http import HttpClient

BASE = "http://test.local/api/v1"


def make(routes):
    counts = {}

    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        counts[key] = counts.get(key, 0) + 1
        status, body = routes[key](counts[key])
        return httpx.Response(status) if body is None else httpx.Response(status, json=body)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client, counts


@pytest.mark.asyncio
async def test_error_mapping():
    client, _ = make({
        "GET /api/v1/x": lambda n: (404, {"error": {"code": "NOT_FOUND", "message": "no"}}),
        "GET /api/v1/y": lambda n: (400, {"error": {"code": "BAD", "message": "bad"}}),
        "POST /api/v1/z": lambda n: (409, {"error": {"code": "CONFLICT", "message": "c"}}),
    })
    http = HttpClient(BASE, max_retries=0, client=client)
    with pytest.raises(NotFoundError):
        await http.get("/x")
    with pytest.raises(ValidationError):
        await http.get("/y")
    with pytest.raises(ConflictError):
        await http.post("/z")


@pytest.mark.asyncio
async def test_retry_get_on_500():
    client, counts = make({
        "GET /api/v1/flaky": lambda n: (500, {"error": {"code": "X", "message": "x"}}) if n < 3 else (200, {"ok": True}),
    })
    http = HttpClient(BASE, max_retries=3, client=client)
    res = await http.get("/flaky")
    assert res["ok"] is True
    assert counts["GET /api/v1/flaky"] == 3


@pytest.mark.asyncio
async def test_no_retry_post_on_500():
    client, counts = make({
        "POST /api/v1/write": lambda n: (500, {"error": {"code": "X", "message": "x"}}),
    })
    http = HttpClient(BASE, max_retries=3, client=client)
    with pytest.raises(Exception):
        await http.post("/write")
    assert counts["POST /api/v1/write"] == 1


@pytest.mark.asyncio
async def test_delete_targets_path():
    client, counts = make({"DELETE /api/v1/saved-listings/abc": lambda n: (204, None)})
    http = HttpClient(BASE, client=client)
    await http.delete("/saved-listings/abc")
    assert counts["DELETE /api/v1/saved-listings/abc"] == 1


@pytest.mark.asyncio
async def test_401_refresh_then_retry():
    store = TokenStore(None, "refresh-token")
    client, counts = make({
        "POST /api/v1/auth/refresh": lambda n: (200, {"token": "new-access"}),
        "GET /api/v1/secure": lambda n: (401, {"error": {"code": "U", "message": "no"}}) if n < 2 else (200, {"ok": True}),
    })
    http = HttpClient(BASE, token_provider=lambda: store.access, client=client)
    auth = AuthResource(http, store)
    http.on_unauthorized = auth.try_refresh
    res = await http.get("/secure")
    assert res["ok"] is True
    assert store.access == "new-access"
    assert counts["GET /api/v1/secure"] == 2
