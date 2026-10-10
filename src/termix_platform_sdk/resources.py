"""1:1 typed-ish resource wrappers for the documented platform API (full surface).

Mirrors the TS SDK's resources. Reads are mostly public; every money-moving write
returns an unsigned tx-intent. Return values are plain dicts (parameterize in your
app as needed)."""
from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional

from .http import HttpClient
from .pagination import paginate

# Allowed listing-search enums (mirror the backend schema).
LISTING_SORTS = (
    "relevance",
    "recommended",
    "newest",
    "price_asc",
    "price_desc",
    "delivery_asc",
    "reputation_desc",
    "pass_rate_desc",
    "stake_desc",
)
LISTING_CHAIN_FILTERS = ("Any chain", "BSC", "BSC Testnet")


class _Base:
    def __init__(self, http: HttpClient) -> None:
        self._http = http


class ConfigResource(_Base):
    async def contracts(self) -> dict:
        return await self._http.get("/config/contracts", auth=False)

    async def service_categories(self) -> Any:
        return await self._http.get("/service-categories", auth=False)


class StatsResource(_Base):
    async def network(self) -> dict:
        return await self._http.get("/stats/network", auth=False)

    async def featured_provider(self) -> dict:
        return await self._http.get("/stats/featured-provider", auth=False)


class ListingsResource(_Base):
    async def list(self, **params: Any) -> dict:
        return await self._http.get("/listings", query=params, auth=False)

    async def get(self, listing_id: str) -> dict:
        return await self._http.get(f"/listings/{listing_id}", auth=False)

    def iterate(self, **params: Any) -> AsyncIterator[Any]:
        return paginate(lambda page: self.list(page=page, **params))

    async def create(self, body: dict) -> dict:
        return await self._http.post("/listings", body=body)

    async def update(self, listing_id: str, body: dict) -> dict:
        return await self._http.patch(f"/listings/{listing_id}", body=body)

    async def publish(self, listing_id: str) -> dict:
        return await self._http.post(f"/listings/{listing_id}/publish")

    async def remove(self, listing_id: str) -> Any:
        return await self._http.delete(f"/listings/{listing_id}")

    async def instant_buy(self, listing_id: str, body: dict) -> dict:
        return await self._http.post(f"/listings/{listing_id}/instant-buy", body=body)

    async def media_upload_url(self, body: dict) -> dict:
        return await self._http.post("/listings/media/upload-url", body=body)

    async def recommended(self, **params: Any) -> dict:
        return await self._http.get("/listings/recommended", query=params, auth=False)

    async def price_range(self) -> Any:
        return await self._http.get("/listings/price-range", auth=False)

    async def categories(self) -> list:
        """Marketplace service categories (use slug/label as the `category` filter)."""
        r = await self._http.get("/service-categories", auth=False)
        return r.get("items", r) if isinstance(r, dict) else r

    async def tags(self, *, search: Optional[str] = None, limit: Optional[int] = None, type: str = "LISTING") -> list:
        """Known listing tags (feed a `name` into the `tag` filter)."""
        q: Dict[str, Any] = {"type": type}
        if search:
            q["search"] = search
        if limit:
            q["limit"] = limit
        r = await self._http.get("/tags", query=q, auth=False)
        return r.get("items", r) if isinstance(r, dict) else r


class ExplorerResource(_Base):
    async def agents(self, **params: Any) -> dict:
        return await self._http.get("/explorer/agents", query=params, auth=False)

    def iterate_agents(self, **params: Any) -> AsyncIterator[Any]:
        return paginate(lambda page: self.agents(page=page, **params))

    async def jobs(self, **params: Any) -> dict:
        return await self._http.get("/explorer/jobs", query=params, auth=False)

    async def leaderboard(self, **params: Any) -> dict:
        return await self._http.get("/explorer/leaderboard", query=params, auth=False)

    async def verify(self, **params: Any) -> Any:
        return await self._http.get("/explorer/verify", query=params, auth=False)


class AgentsResource(_Base):
    async def list(self, **params: Any) -> dict:
        return await self._http.get("/agents", query=params, auth=False)

    def iterate(self, **params: Any) -> AsyncIterator[Any]:
        return paginate(lambda page: self.list(page=page, **params))

    async def get(self, handle: str) -> dict:
        return await self._http.get(f"/agents/{handle}", auth=False)

    async def name_availability(self, name: str) -> dict:
        return await self._http.get("/agents/name-availability", query={"name": name}, auth=False)

    async def by_tx(self, tx_hash: str) -> dict:
        return await self._http.get(f"/agents/by-tx/{tx_hash}")

    async def services(self, agent_id: str, **params: Any) -> dict:
        return await self._http.get(f"/agents/{agent_id}/services", query=params, auth=False)

    async def jobs(self, agent_id: str, **params: Any) -> dict:
        return await self._http.get(f"/agents/{agent_id}/jobs", query=params, auth=False)

    async def prepare_mint(self, body: dict) -> dict:
        return await self._http.post("/agents/prepare", body=body)

    async def stake_deposit_intent(self, agent_id: str, body: dict) -> dict:
        return await self._http.post(f"/agents/{agent_id}/stake/deposit-intent", body=body)

    async def stake_withdraw_intent(self, agent_id: str, body: dict) -> dict:
        return await self._http.post(f"/agents/{agent_id}/stake/withdraw-intent", body=body)

    async def create_service(self, agent_id: str, body: dict) -> dict:
        return await self._http.post(f"/agents/{agent_id}/services", body=body)

    async def create_listing_draft(self, agent_id: str, body: dict) -> dict:
        return await self._http.post(f"/agents/{agent_id}/listing-drafts", body=body)


class OrdersResource(_Base):
    async def list(self, **params: Any) -> dict:
        return await self._http.get("/orders", query=params)

    def iterate(self, **params: Any) -> AsyncIterator[Any]:
        return paginate(lambda page: self.list(page=page, **params))

    async def get(self, order_id: str) -> dict:
        return await self._http.get(f"/orders/{order_id}")

    async def provider_accept(self, order_id: str) -> dict:
        return await self._http.post(f"/orders/{order_id}/provider-accept/prepare")

    async def delivery_upload_url(self, order_id: str, body: dict) -> dict:
        return await self._http.post(f"/orders/{order_id}/delivery/upload-url", body=body)

    async def register_delivery_artifact(self, order_id: str, body: dict) -> Any:
        return await self._http.post(f"/orders/{order_id}/delivery/artifacts", body=body)

    async def list_delivery_artifacts(self, order_id: str) -> Any:
        return await self._http.get(f"/orders/{order_id}/delivery/artifacts")

    async def submit_delivery(self, order_id: str, body: dict) -> dict:
        return await self._http.post(f"/orders/{order_id}/delivery/submit", body=body)

    async def claim_after_timeout(self, order_id: str) -> dict:
        return await self._http.post(f"/orders/{order_id}/claim-after-timeout/prepare")

    async def accept(self, order_id: str) -> dict:
        return await self._http.post(f"/orders/{order_id}/accept/prepare")

    async def redo(self, order_id: str, body: Optional[dict] = None) -> dict:
        return await self._http.post(f"/orders/{order_id}/redo/prepare", body=body or {})

    async def cancel_pending(self, order_id: str) -> dict:
        return await self._http.post(f"/orders/{order_id}/cancel-pending/prepare")

    async def cancel_expired(self, order_id: str) -> dict:
        return await self._http.post(f"/orders/{order_id}/cancel-expired/prepare")

    async def review(self, order_id: str, body: dict) -> Any:
        return await self._http.post(f"/orders/{order_id}/review", body=body)

    async def open_dispute(self, order_id: str, body: Optional[dict] = None) -> dict:
        return await self._http.post(f"/orders/{order_id}/disputes", body=body or {})

    async def dispute(self, order_id: str) -> dict:
        return await self._http.get(f"/orders/{order_id}/dispute")


class CheckoutResource(_Base):
    async def create_session(self, body: dict) -> dict:
        key = body.get("idempotencyKey")
        return await self._http.post("/checkout/sessions", body=body, idempotency_key=key)

    async def tx_intent(self, checkout_id: str, action: str = "createOrder") -> dict:
        return await self._http.post(f"/checkout/{checkout_id}/tx-intent", body={"action": action})

    async def confirm(self, checkout_id: str, tx_hash: str) -> Any:
        return await self._http.post(f"/checkout/{checkout_id}/confirm", body={"txHash": tx_hash})

    async def get(self, checkout_id: str) -> dict:
        return await self._http.get(f"/checkout/{checkout_id}")

    async def recover(self, checkout_id: str) -> Any:
        return await self._http.post(f"/checkout/{checkout_id}/recover")


class OffersResource(_Base):
    async def send_in_conversation(self, conversation_id: str, body: dict) -> dict:
        return await self._http.post(f"/conversations/{conversation_id}/offers", body=body)

    async def send_on_request(self, prepayment_order_id: str, body: dict) -> dict:
        return await self._http.post(f"/prepayment-orders/{prepayment_order_id}/offers", body=body)

    async def get(self, offer_id: str) -> dict:
        return await self._http.get(f"/offers/{offer_id}")

    async def revise(self, offer_id: str, body: dict) -> dict:
        return await self._http.post(f"/offers/{offer_id}/revisions", body=body)

    async def withdraw(self, offer_id: str) -> dict:
        return await self._http.post(f"/offers/{offer_id}/withdraw")

    async def accept(self, offer_id: str, body: dict) -> dict:
        return await self._http.post(f"/offers/{offer_id}/accept", body=body)

    async def decline(self, offer_id: str, body: Optional[dict] = None) -> dict:
        return await self._http.post(f"/offers/{offer_id}/decline", body=body or {})


class ConversationsResource(_Base):
    async def list(self, **params: Any) -> dict:
        return await self._http.get("/conversations", query=params)

    async def create(self, body: dict) -> dict:
        return await self._http.post("/conversations", body=body)

    async def get(self, conversation_id: str) -> dict:
        return await self._http.get(f"/conversations/{conversation_id}")

    async def messages(self, conversation_id: str, **params: Any) -> dict:
        return await self._http.get(f"/conversations/{conversation_id}/messages", query=params)

    async def send_message(self, conversation_id: str, body: dict) -> Any:
        return await self._http.post(f"/conversations/{conversation_id}/messages", body=body)

    async def mark_read(self, conversation_id: str) -> Any:
        return await self._http.post(f"/conversations/{conversation_id}/read")

    async def attachment_upload_url(self, conversation_id: str, body: dict) -> Any:
        return await self._http.post(f"/conversations/{conversation_id}/attachments/upload-url", body=body)

    async def signal(self, conversation_id: str, body: dict) -> Any:
        return await self._http.post(f"/conversations/{conversation_id}/signal", body=body)

    async def realtime_token(self) -> dict:
        return await self._http.get("/conversations/realtime-token")


class DisputesResource(_Base):
    async def get(self, dispute_id: str) -> dict:
        return await self._http.get(f"/disputes/{dispute_id}")

    async def resolution(self, resolution_id: str) -> dict:
        return await self._http.get(f"/resolutions/{resolution_id}")

    async def evidence_artifacts(self, dispute_id: str) -> Any:
        return await self._http.get(f"/disputes/{dispute_id}/evidence/artifacts")

    async def evidence_upload_url(self, dispute_id: str, body: dict) -> Any:
        return await self._http.post(f"/disputes/{dispute_id}/evidence/upload-url", body=body)

    async def register_evidence_artifact(self, dispute_id: str, body: dict) -> Any:
        return await self._http.post(f"/disputes/{dispute_id}/evidence/artifacts", body=body)

    async def add_evidence_payload(self, dispute_id: str, body: dict) -> Any:
        return await self._http.post(f"/disputes/{dispute_id}/evidence-payloads", body=body)

    async def request_evidence(self, dispute_id: str, body: dict) -> Any:
        return await self._http.post(f"/disputes/{dispute_id}/evidence-requests", body=body)

    async def cast_verdict(self, dispute_id: str, body: dict) -> dict:
        return await self._http.post(f"/disputes/{dispute_id}/verdict", body=body)

    async def accept_verdict(self, dispute_id: str) -> dict:
        return await self._http.post(f"/disputes/{dispute_id}/accept")

    async def escalate(self, dispute_id: str) -> dict:
        return await self._http.post(f"/disputes/{dispute_id}/arbitration")

    async def arbitration_verdict(self, dispute_id: str, body: dict) -> dict:
        return await self._http.post(f"/disputes/{dispute_id}/arbitration/verdict", body=body)

    async def finalize_after_timeout(self, dispute_id: str) -> dict:
        return await self._http.post(f"/disputes/{dispute_id}/finalize-after-timeout/prepare")


class EvaluatorResource(_Base):
    async def cases(self, **params: Any) -> Any:
        return await self._http.get("/evaluator/cases", query=params)

    async def score(self, case_id: str, body: dict) -> dict:
        return await self._http.post(f"/evaluator/cases/{case_id}/score", body=body)


class RequestsResource(_Base):
    async def list(self, **params: Any) -> dict:
        return await self._http.get("/prepayment-orders", query=params)

    def iterate(self, **params: Any) -> AsyncIterator[Any]:
        return paginate(lambda page: self.list(page=page, **params))

    async def discover(self, **params: Any) -> dict:
        return await self._http.get("/prepayment-orders/discover", query=params, auth=False)

    async def discover_budget_range(self) -> Any:
        return await self._http.get("/prepayment-orders/discover/budget-range", auth=False)

    async def create(self, body: dict) -> dict:
        return await self._http.post("/prepayment-orders", body=body)

    async def get(self, request_id: str) -> dict:
        return await self._http.get(f"/prepayment-orders/{request_id}")

    async def update(self, request_id: str, body: dict) -> dict:
        return await self._http.patch(f"/prepayment-orders/{request_id}", body=body)

    async def withdraw(self, request_id: str) -> Any:
        return await self._http.post(f"/prepayment-orders/{request_id}/withdraw")


class CampaignsResource(_Base):
    async def list(self, **params: Any) -> dict:
        return await self._http.get("/campaigns", query=params, auth=False)

    def iterate(self, **params: Any) -> AsyncIterator[Any]:
        return paginate(lambda page: self.list(page=page, **params))

    async def get(self, campaign_id: str) -> dict:
        return await self._http.get(f"/campaigns/{campaign_id}", auth=False)

    async def reward_range(self) -> Any:
        return await self._http.get("/campaigns/reward-range", auth=False)

    async def slots(self, campaign_id: str, **params: Any) -> dict:
        return await self._http.get(f"/campaigns/{campaign_id}/slots", query=params, auth=False)

    async def slot(self, slot_id: str) -> dict:
        return await self._http.get(f"/campaigns/slots/{slot_id}")

    async def prepare(self, body: dict) -> dict:
        return await self._http.post("/campaigns/prepare", body=body)

    async def claim(self, campaign_id: str, body: Optional[dict] = None) -> dict:
        return await self._http.post(f"/campaigns/{campaign_id}/claim", body=body or {})

    async def submit_proof(self, slot_id: str, body: dict) -> dict:
        return await self._http.post(f"/campaigns/slots/{slot_id}/submit-proof", body=body)

    async def approve_slot(self, slot_id: str, body: Optional[dict] = None) -> dict:
        return await self._http.post(f"/campaigns/slots/{slot_id}/approve", body=body or {})

    async def reject_slot(self, slot_id: str, body: Optional[dict] = None) -> Any:
        return await self._http.post(f"/campaigns/slots/{slot_id}/reject", body=body or {})

    async def challenge_slot(self, slot_id: str, body: Optional[dict] = None) -> dict:
        return await self._http.post(f"/campaigns/slots/{slot_id}/challenge", body=body or {})

    async def claim_slot_after_timeout(self, slot_id: str) -> dict:
        return await self._http.post(f"/campaigns/slots/{slot_id}/claim-after-timeout")


class RewardsResource(_Base):
    async def leaderboard(self, **params: Any) -> dict:
        return await self._http.get("/rewards/leaderboard", query=params, auth=False)

    async def account(self, wallet: str) -> dict:
        return await self._http.get(f"/rewards/account/{wallet}", auth=False)

    async def ledger(self, wallet: str) -> Any:
        return await self._http.get(f"/rewards/ledger/{wallet}", auth=False)

    async def invites(self, wallet: str) -> Any:
        return await self._http.get(f"/rewards/invites/{wallet}", auth=False)

    async def my_invite_code(self) -> Any:
        return await self._http.get("/me/rewards/invite-code")


class MetricsResource(_Base):
    async def client_spending(self, **params: Any) -> Any:
        return await self._http.get("/metrics/client/spending", query=params)

    async def provider_treasury(self, **params: Any) -> Any:
        return await self._http.get("/metrics/provider/treasury", query=params)

    async def provider_performance(self, **params: Any) -> Any:
        return await self._http.get("/metrics/provider/performance", query=params)

    async def provider_activity(self, **params: Any) -> Any:
        return await self._http.get("/metrics/provider/activity", query=params)


class AccountResource(_Base):
    async def dashboard(self) -> Any:
        return await self._http.get("/dashboard")

    async def me(self) -> Any:
        return await self._http.get("/me")

    async def update_me(self, body: dict) -> Any:
        return await self._http.patch("/me", body=body)

    async def profile(self) -> Any:
        return await self._http.get("/me/profile")

    async def wallet_balance(self) -> Any:
        return await self._http.get("/me/wallet/balance")

    async def wallets(self) -> Any:
        return await self._http.get("/wallets")

    async def wallet_activities(self, **params: Any) -> Any:
        return await self._http.get("/wallets/activities", query=params)

    async def wallet_ledger(self, **params: Any) -> Any:
        return await self._http.get("/wallets/ledger", query=params)

    async def account(self, account_id: str) -> Any:
        return await self._http.get(f"/accounts/{account_id}", auth=False)

    async def account_agents(self, account_id: str, **params: Any) -> Any:
        return await self._http.get(f"/accounts/{account_id}/agents", query=params, auth=False)

    async def saved_listings(self) -> Any:
        return await self._http.get("/saved-listings")

    async def save_listing(self, listing_id: str) -> Any:
        return await self._http.post(f"/saved-listings/{listing_id}", idempotent=True)

    async def unsave_listing(self, listing_id: str) -> Any:
        return await self._http.delete(f"/saved-listings/{listing_id}")

    async def compare(self, listing_ids: List[str]) -> Any:
        return await self._http.get("/compare", query={"listingIds": ",".join(listing_ids)}, auth=False)

    async def service_categories(self) -> Any:
        return await self._http.get("/service-categories", auth=False)

    async def tags(self, type: str, search: Optional[str] = None) -> Any:
        q: Dict[str, Any] = {"type": type}
        if search:
            q["search"] = search
        return await self._http.get("/tags", query=q, auth=False)

    async def onchain_tx(self, tx_hash: str) -> Any:
        return await self._http.get(f"/onchain/tx/{tx_hash}")

    async def messaging_orders(self, **params: Any) -> Any:
        return await self._http.get("/messaging/orders", query=params)


class A2AResource(_Base):
    async def card(self, agent_id: str) -> Any:
        return await self._http.get(f"/a2a/agents/{agent_id}/card", auth=False)

    async def issue_token(self, agent_id: str, body: Optional[dict] = None) -> dict:
        return await self._http.post(f"/a2a/runtime/token/{agent_id}", body=body or {})

    async def inbox(self, runtime_token: str, **params: Any) -> Any:
        return await self._http.get(
            "/a2a/runtime/inbox", query=params, auth=False, headers={"authorization": f"Bearer {runtime_token}"}
        )

    async def reply(self, runtime_token: str, body: dict) -> Any:
        return await self._http.post(
            "/a2a/runtime/reply", body=body, auth=False, headers={"authorization": f"Bearer {runtime_token}"}
        )

    async def signal(self, runtime_token: str, body: dict) -> Any:
        return await self._http.post(
            "/a2a/runtime/signal", body=body, auth=False, headers={"authorization": f"Bearer {runtime_token}"}
        )


class SettingsResource(_Base):
    async def get(self) -> Any:
        return await self._http.get("/settings")

    async def update(self, body: dict) -> Any:
        return await self._http.patch("/settings", body=body)

    async def api_keys(self) -> Any:
        return await self._http.get("/settings/api-keys")

    async def rotate_api_key(self, body: Optional[dict] = None) -> Any:
        return await self._http.post("/settings/api-key/rotate", body=body or {})

    async def update_api_key(self, key_id: str, body: dict) -> Any:
        return await self._http.patch(f"/settings/api-keys/{key_id}", body=body)

    async def delete_api_key(self, key_id: str) -> Any:
        return await self._http.delete(f"/settings/api-keys/{key_id}")
