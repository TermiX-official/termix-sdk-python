"""Business-flow orchestration (state-reconciling, dual signing modes)."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .chain import broadcast_intent, wait_for
from .errors import ChainError, NotFoundError


def _idem(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _extract_intents(resp: Any) -> List[dict]:
    out: List[dict] = []
    if not isinstance(resp, dict):
        return out

    def push(v: Any) -> None:
        if isinstance(v, dict) and "callData" in v and "contract" in v:
            out.append(v)

    push(resp.get("bondApprovalTxIntent"))
    push(resp.get("openChallenge"))
    push(resp.get("txIntent"))
    for v in resp.get("txIntents") or []:
        push(v)
    push(resp)
    return out


class Flows:
    def __init__(self, client: "Any") -> None:
        self._c = client

    async def _broadcast(self, intent: dict, auto_sign: bool) -> Optional[str]:
        if not auto_sign:
            return None
        signer = self._c.signer
        if signer is None:
            raise ChainError("auto_sign requires a signer on the client (mode B)")
        # Some intents (e.g. agent mint /agents/prepare) omit chainId; fill from config.
        if not intent.get("chainId"):
            cfg = await self._c.contracts()
            intent = {**intent, "chainId": cfg.get("chainId")}
        return await broadcast_intent(signer, intent)

    async def register_agent(
        self, handle: str, *, mint: Optional[dict] = None, auto_sign: bool = False, wait: Optional[dict] = None
    ) -> Dict[str, Any]:
        avail = await self._c.agents.name_availability(handle)
        if isinstance(avail, dict) and avail.get("available") is False:
            raise ValueError(f"agent handle not available: {handle}")
        intent = await self._c.agents.prepare_mint({"name": handle, **(mint or {})})
        tx = await self._broadcast(intent, auto_sign)
        if not tx:
            return {"intents": [intent], "tx_hashes": [], "result": None}

        async def _read() -> Any:
            try:
                return await self._c.agents.by_tx(tx)
            except NotFoundError:
                return None

        # The mint tx is broadcast; agent resolution depends on the indexer, which can
        # lag. Never discard a successful broadcast — return the hash even if resolution
        # times out so the caller can poll agents.by_tx(tx) later.
        try:
            agent = await wait_for(_read, lambda a: isinstance(a, dict) and bool(a.get("id")), **(wait or {}))
        except TimeoutError:
            agent = None
        return {"intents": [intent], "tx_hashes": [tx], "result": agent}

    async def complete_checkout(self, checkout_id: str, *, auto_sign: bool = False, wait: Optional[dict] = None) -> Dict[str, Any]:
        approve = await self._c.checkout.tx_intent(checkout_id, "approveEscrow")
        approve_hash = await self._broadcast(approve, auto_sign)
        signer = self._c.signer
        # ERC-20 approve must be mined before createOrder (transferFrom) or it reverts.
        if approve_hash and signer is not None and hasattr(signer, "wait_for_receipt"):
            await signer.wait_for_receipt(approve_hash, approve.get("chainId"))
        create = await self._c.checkout.tx_intent(checkout_id, "createOrder")
        create_hash = await self._broadcast(create, auto_sign)

        intents = [approve, create]
        tx_hashes = [h for h in (approve_hash, create_hash) if h]
        if not create_hash:
            return {"intents": intents, "tx_hashes": tx_hashes, "result": None}

        await self._c.checkout.confirm(checkout_id, create_hash)
        session = await wait_for(
            lambda: self._c.checkout.get(checkout_id),
            lambda s: bool(s.get("orderId")) or s.get("status") == "CONFIRMED",
            **(wait or {}),
        )
        order = await self._c.orders.get(session["orderId"]) if session.get("orderId") else None
        return {"intents": intents, "tx_hashes": tx_hashes, "result": order}

    async def buy_listing(
        self, listing_id: str, *, client_agent_id: str, auto_sign: bool = False, wait: Optional[dict] = None, **body: Any
    ) -> Dict[str, Any]:
        res = await self._c.listings.instant_buy(listing_id, {"clientAgentId": client_agent_id, **body})
        checkout_id = str(res.get("checkoutId") or res.get("id") or (res.get("checkout") or {}).get("id") or "")
        if not checkout_id:
            raise ValueError("instant-buy did not return a checkout id")
        return await self.complete_checkout(checkout_id, auto_sign=auto_sign, wait=wait)

    async def accept_offer_and_checkout(
        self,
        offer_id: str,
        *,
        revision_id: str,
        client_agent_id: str,
        expected_version: Optional[int] = None,
        desired_stake: Optional[str] = None,
        auto_sign: bool = False,
        wait: Optional[dict] = None,
    ) -> Dict[str, Any]:
        accept_body: Dict[str, Any] = {"revisionId": revision_id, "clientAgentId": client_agent_id}
        if expected_version is not None:
            accept_body["expectedVersion"] = expected_version
        await self._c.offers.accept(offer_id, accept_body)
        session_body: Dict[str, Any] = {
            "offerId": offer_id,
            "revisionId": revision_id,
            "clientAgentId": client_agent_id,
            "idempotencyKey": _idem(f"checkout-{offer_id}"),
        }
        if desired_stake:
            session_body["desiredStake"] = desired_stake
        session = await self._c.checkout.create_session(session_body)
        return await self.complete_checkout(session["id"], auto_sign=auto_sign, wait=wait)

    async def accept_order_as_provider(self, order_id: str, *, auto_sign: bool = False, wait: Optional[dict] = None) -> Dict[str, Any]:
        intent = await self._c.orders.provider_accept(order_id)
        return await self._single(order_id, intent, lambda o: o.get("status") in ("FUNDED", "IN_PROGRESS"), auto_sign, wait)

    async def deliver(
        self,
        order_id: str,
        *,
        artifact_ids: Optional[List[str]] = None,
        delivery_hash: Optional[str] = None,
        note: Optional[str] = None,
        auto_sign: bool = False,
        wait: Optional[dict] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if artifact_ids is not None:
            body["artifactIds"] = artifact_ids
        if delivery_hash is not None:
            body["deliveryHash"] = delivery_hash
        if note is not None:
            body["note"] = note
        intent = await self._c.orders.submit_delivery(order_id, body)
        return await self._single(order_id, intent, lambda o: o.get("status") == "DELIVERED", auto_sign, wait)

    async def settle(self, order_id: str, *, auto_sign: bool = False, wait: Optional[dict] = None) -> Dict[str, Any]:
        intent = await self._c.orders.accept(order_id)
        return await self._single(order_id, intent, lambda o: o.get("status") == "SETTLED", auto_sign, wait)

    async def redo(self, order_id: str, *, note: Optional[str] = None, auto_sign: bool = False, wait: Optional[dict] = None) -> Dict[str, Any]:
        intent = await self._c.orders.redo(order_id, {"note": note} if note else {})
        return await self._single(order_id, intent, lambda o: o.get("redoUsed") is True, auto_sign, wait)

    async def cancel_expired(self, order_id: str, *, auto_sign: bool = False, wait: Optional[dict] = None) -> Dict[str, Any]:
        intent = await self._c.orders.cancel_expired(order_id)
        return await self._single(order_id, intent, lambda o: o.get("status") == "CANCELLED", auto_sign, wait)

    async def claim_after_timeout(self, order_id: str, *, auto_sign: bool = False, wait: Optional[dict] = None) -> Dict[str, Any]:
        intent = await self._c.orders.claim_after_timeout(order_id)
        return await self._single(order_id, intent, lambda o: o.get("status") == "SETTLED", auto_sign, wait)

    async def open_dispute(self, order_id: str, *, auto_sign: bool = False, wait: Optional[dict] = None, **body: Any) -> Dict[str, Any]:
        prep = await self._c.orders.open_dispute(order_id, body or {})
        intents = _extract_intents(prep)
        tx_hashes: List[str] = []
        if auto_sign:
            signer = self._c.signer
            for i, intent in enumerate(intents):
                h = await self._broadcast(intent, True)
                if h:
                    tx_hashes.append(h)
                    # When multiple sequential intents exist (e.g. bond approval before contract call),
                    # the prior transaction must be mined before the next transaction can succeed.
                    if i < len(intents) - 1 and signer is not None and hasattr(signer, "wait_for_receipt"):
                        await signer.wait_for_receipt(h, intent.get("chainId"))
        if not auto_sign or not tx_hashes:
            return {"intents": intents, "tx_hashes": tx_hashes, "result": None}
        order = await wait_for(lambda: self._c.orders.get(order_id), lambda o: o.get("status") == "IN_DISPUTE", **(wait or {}))
        return {"intents": intents, "tx_hashes": tx_hashes, "result": order}

    async def _single(self, order_id: str, intent: dict, done, auto_sign: bool, wait: Optional[dict]) -> Dict[str, Any]:
        tx = await self._broadcast(intent, auto_sign)
        if not tx:
            return {"intents": [intent], "tx_hashes": [], "result": None}
        order = await wait_for(lambda: self._c.orders.get(order_id), done, **(wait or {}))
        return {"intents": [intent], "tx_hashes": [tx], "result": order}
