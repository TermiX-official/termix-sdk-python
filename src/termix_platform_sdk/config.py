"""Authoritative chain registry (verified against the skill registry + live prod)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import re


@dataclass(frozen=True)
class ChainEndpoint:
    key: str
    chain_id: int
    label: str
    host: str  # without /api/v1


CHAINS = {
    "bsc": ChainEndpoint("bsc", 56, "BNB Chain", "https://platform-backend.prod.termix.live"),
    "base": ChainEndpoint("base", 8453, "Base", "https://platform-backend-base.prod.termix.live"),
    "rh": ChainEndpoint("rh", 4663, "Robinhood Chain", "https://platform-backend-rh.prod.termix.live"),
}

DEFAULT_CHAIN = "bsc"


def resolve_base_url(chain: Optional[str] = None, base_url: Optional[str] = None) -> str:
    if base_url:
        b = base_url.rstrip("/")
        return b if re.search(r"/api/v\d+$", b) else f"{b}/api/v1"
    endpoint = CHAINS[chain or DEFAULT_CHAIN]
    return f"{endpoint.host}/api/v1"
