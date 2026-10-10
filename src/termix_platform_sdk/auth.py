"""SIWE auth + token store (async). API keys / A2A tokens wired via the client."""
from __future__ import annotations

from typing import Any, Optional

from .chain import Signer
from .http import HttpClient

_KEEP = object()


class TokenStore:
    def __init__(self, access: Optional[str] = None, refresh: Optional[str] = None) -> None:
        self.access = access
        self.refresh = refresh

    def set(self, access: Optional[str], refresh: Any = _KEEP) -> None:
        self.access = access
        if refresh is not _KEEP:
            self.refresh = refresh

    def clear(self) -> None:
        self.access = None
        self.refresh = None


class AuthResource:
    def __init__(self, http: HttpClient, store: TokenStore) -> None:
        self._http = http
        self._store = store

    @property
    def token(self) -> Optional[str]:
        return self._store.access

    async def nonce(self, wallet_address: str, *, domain: Optional[str] = None, chain_id: Optional[int] = None) -> dict:
        body: dict = {"walletAddress": wallet_address}
        if domain:
            body["domain"] = domain
        if chain_id:
            body["chainId"] = chain_id
        return await self._http.post("/auth/nonce", body=body, auth=False)

    async def login_with_siwe(self, signer: Signer, chain_id: int, domain: Optional[str] = None) -> dict:
        # /auth/wallet is strict: { walletAddress, nonce, signature, domain?, chainId? }.
        # Sign the `message` returned by /auth/nonce (eip191) and echo nonce + domain/chainId.
        address = await signer.get_address()
        n = await self.nonce(address, domain=domain, chain_id=chain_id)
        signature = await signer.sign_message(n.get("message") or n.get("nonce"))
        body: dict = {"walletAddress": address, "nonce": n["nonce"], "signature": signature}
        if n.get("domain"):
            body["domain"] = n["domain"]
        if n.get("chainId"):
            body["chainId"] = n["chainId"]
        res = await self._http.post("/auth/wallet", body=body, auth=False)
        self._store.set(res.get("token") or res.get("accessToken"), res.get("refreshToken"))
        return res

    async def try_refresh(self) -> bool:
        if not self._store.refresh:
            return False
        try:
            res = await self._http.post("/auth/refresh", body={"refreshToken": self._store.refresh}, auth=False)
        except Exception:
            return False
        access = res.get("token") or res.get("accessToken")
        if not access:
            return False
        self._store.set(access, res.get("refreshToken") or self._store.refresh)
        return True

    async def logout(self) -> None:
        if self._store.refresh:
            try:
                await self._http.post("/auth/logout", body={"refreshToken": self._store.refresh})
            except Exception:
                pass
        self._store.clear()
