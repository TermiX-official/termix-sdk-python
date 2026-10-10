"""TermixClient — assembles transport, auth, resources, flows, realtime."""
from __future__ import annotations

from typing import Any, List, Optional

import httpx

import warnings

from .auth import AuthResource, TokenStore
from .config import CHAINS, resolve_base_url
from .flows import Flows
from .http import HttpClient
from .realtime import RealtimeResource
from .resources import (
    A2AResource,
    AccountResource,
    AgentsResource,
    CampaignsResource,
    CheckoutResource,
    ConfigResource,
    ConversationsResource,
    DisputesResource,
    EvaluatorResource,
    ExplorerResource,
    ListingsResource,
    MetricsResource,
    OffersResource,
    OrdersResource,
    RequestsResource,
    RewardsResource,
    SettingsResource,
    StatsResource,
)


class TermixClient:
    def __init__(
        self,
        *,
        chain: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = 30.0,
        max_retries: int = 2,
        token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        api_key: Optional[str] = None,
        signer: Any = None,
        interceptors: Optional[List[dict]] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        on_warning: Optional[Any] = None,
    ) -> None:
        self._store = TokenStore(token, refresh_token)
        self.signer = signer
        self._contracts: Optional[dict] = None
        self._chain = chain
        self._base_url_override = bool(base_url)
        self._on_warning = on_warning or (lambda m: warnings.warn(f"[termix] {m}", stacklevel=2))
        self._compat_checked = False

        def token_provider() -> Optional[str]:
            return self._store.access or api_key

        self.http = HttpClient(
            resolve_base_url(chain, base_url),
            timeout_s=timeout_s,
            max_retries=max_retries,
            token_provider=token_provider,
            on_unauthorized=self._on_unauthorized,
            interceptors=interceptors,
            client=http_client,
        )
        self.auth = AuthResource(self.http, self._store)
        self.config = ConfigResource(self.http)
        self.stats = StatsResource(self.http)
        self.listings = ListingsResource(self.http)
        self.explorer = ExplorerResource(self.http)
        self.agents = AgentsResource(self.http)
        self.orders = OrdersResource(self.http)
        self.offers = OffersResource(self.http)
        self.checkout = CheckoutResource(self.http)
        self.conversations = ConversationsResource(self.http)
        self.disputes = DisputesResource(self.http)
        self.evaluator = EvaluatorResource(self.http)
        self.requests = RequestsResource(self.http)
        self.campaigns = CampaignsResource(self.http)
        self.rewards = RewardsResource(self.http)
        self.metrics = MetricsResource(self.http)
        self.account = AccountResource(self.http)
        self.a2a = A2AResource(self.http)
        self.settings = SettingsResource(self.http)
        self.realtime = RealtimeResource(self.http.base_url, token_provider, client=http_client)
        self.flows = Flows(self)

    async def _on_unauthorized(self) -> bool:
        return await self.auth.try_refresh()

    async def contracts(self, force: bool = False) -> dict:
        if self._contracts is None or force:
            self._contracts = await self.config.contracts()
            self._check_compat(self._contracts)
        return self._contracts

    def _check_compat(self, cfg: dict) -> None:
        # Warn once if the live backend chainId mismatches the requested named chain.
        if self._compat_checked:
            return
        self._compat_checked = True
        if self._chain and not self._base_url_override:
            expected = CHAINS[self._chain].chain_id
            if cfg.get("chainId") != expected:
                self._on_warning(
                    f'backend chainId {cfg.get("chainId")} does not match expected {expected} for chain "{self._chain}"'
                )

    async def aclose(self) -> None:
        await self.http.aclose()

    async def __aenter__(self) -> "TermixClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()


async def create_client(**kwargs: Any) -> TermixClient:
    client = TermixClient(**kwargs)
    await client.contracts()
    return client
