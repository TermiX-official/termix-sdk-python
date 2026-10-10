"""Error model — mirrors the backend `{error:{code,message,details?}}` envelope."""
from __future__ import annotations

from typing import Any, Optional


class TermixError(Exception):
    pass


class TermixApiError(TermixError):
    def __init__(self, status: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(f"[{status} {code}] {message}")
        self.status = status
        self.code = code
        self.details = details


class AuthError(TermixApiError):
    pass


class ValidationError(TermixApiError):
    pass


class NotFoundError(TermixApiError):
    pass


class ConflictError(TermixApiError):
    pass


class RateLimitError(TermixApiError):
    pass


class ServerError(TermixApiError):
    pass


class NetworkError(TermixError):
    pass


class ChainError(TermixError):
    pass


_BY_STATUS = {
    400: ValidationError,
    422: ValidationError,
    401: AuthError,
    403: AuthError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}


def map_api_error(status: int, body: Any) -> TermixApiError:
    err = body.get("error") if isinstance(body, dict) else None
    code = (err or {}).get("code") or ("INTERNAL_ERROR" if status >= 500 else "UNKNOWN")
    message = (err or {}).get("message") or f"HTTP {status}"
    details: Optional[Any] = (err or {}).get("details")
    cls = _BY_STATUS.get(status)
    if cls is not None:
        return cls(status, code, message, details)
    if status >= 500:
        return ServerError(status, code, message, details)
    return TermixApiError(status, code, message, details)
