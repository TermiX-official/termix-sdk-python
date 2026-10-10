"""Python SDK for the TermiX (AACP) marketplace platform API.

Business-flow wrapper (not a thin HTTP client), ported from the TypeScript SDK.
Async-first (httpx); money via Decimal; optional on-chain signing (mode B).
"""
from __future__ import annotations

__version__ = "0.0.0"

from .chain import Signer, TxIntent, broadcast_intent, intent_to_tx, wait_for
from .client import TermixClient, create_client
from .config import CHAINS, DEFAULT_CHAIN, ChainEndpoint, resolve_base_url
from .errors import (
    AuthError,
    ChainError,
    ConflictError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TermixApiError,
    TermixError,
    ValidationError,
)
from .money import from_base_units, to_base_units
from .pagination import collect, paginate
from .resources import LISTING_CHAIN_FILTERS, LISTING_SORTS

__all__ = [
    "__version__",
    "create_client",
    "TermixClient",
    "CHAINS",
    "DEFAULT_CHAIN",
    "ChainEndpoint",
    "resolve_base_url",
    "Signer",
    "TxIntent",
    "intent_to_tx",
    "broadcast_intent",
    "wait_for",
    "to_base_units",
    "from_base_units",
    "paginate",
    "collect",
    "LISTING_SORTS",
    "LISTING_CHAIN_FILTERS",
    "TermixError",
    "TermixApiError",
    "AuthError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ServerError",
    "NetworkError",
    "ChainError",
]
