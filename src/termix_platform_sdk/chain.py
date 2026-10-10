"""Chain primitives: tx-intent, Signer port, and a generic state poller."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Optional, Protocol, TypedDict


class TxIntent(TypedDict, total=False):
    id: str
    accountId: str
    checkoutSessionId: str
    orderId: str
    action: str
    chainId: int
    contract: str
    callData: str
    value: str
    status: str
    txHash: str
    nonceKey: str
    createdAt: str
    confirmedAt: str


class Signer(Protocol):
    """Minimal signer port. viem/ethers/web3.py/Safe adapters implement this."""

    async def get_address(self) -> str: ...
    async def sign_message(self, message: str) -> str: ...
    async def send_transaction(self, tx: dict) -> str: ...
    # optional: async def wait_for_receipt(self, tx_hash: str, chain_id: int) -> None


def intent_to_tx(intent: TxIntent) -> dict:
    value = intent.get("value")
    return {
        "chainId": intent.get("chainId"),
        "to": intent.get("contract"),
        "data": intent.get("callData"),
        "value": value if value and value != "0" else None,
    }


async def broadcast_intent(signer: Signer, intent: TxIntent) -> str:
    return await signer.send_transaction(intent_to_tx(intent))


async def wait_for(
    read: Callable[[], Awaitable[Any]],
    done: Callable[[Any], bool],
    *,
    timeout_s: float = 120.0,
    interval_s: float = 2.0,
) -> Any:
    """Poll a fresh read until `done` — platform state is event-driven, not from the
    broadcast result (only checkout has /confirm; orders/disputes are projected)."""
    deadline = time.monotonic() + timeout_s
    while True:
        value = await read()
        if done(value):
            return value
        if time.monotonic() >= deadline:
            raise TimeoutError(f"wait_for: predicate not satisfied within {timeout_s}s")
        await asyncio.sleep(interval_s)
