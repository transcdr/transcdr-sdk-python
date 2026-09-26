from __future__ import annotations

from typing import List, Optional, cast

from .._base_client import path_segment as seg
from .._base_client import strip_none
from ..pagination import AsyncPage, SyncPage
from ..types import ApiKey
from ._base import AsyncResource, SyncResource

__all__ = ["ApiKeys", "AsyncApiKeys"]


class ApiKeys(SyncResource):
    def list(self, *, limit: Optional[int] = None, cursor: Optional[str] = None) -> SyncPage[ApiKey]:
        return self._client.get_page("/v1/api-keys", {"limit": limit, "cursor": cursor})

    def create(
        self,
        *,
        name: str,
        scopes: Optional[List[str]] = None,
        mode: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> ApiKey:
        """Create a key. The returned ``secret`` is shown only this once."""
        body = strip_none({"name": name, "scopes": scopes, "mode": mode, "expires_at": expires_at})
        return cast(ApiKey, self._client.request("POST", "/v1/api-keys", json=body))

    def delete(self, id: str) -> None:
        """Revoke a key."""
        self._client.request("DELETE", f"/v1/api-keys/{seg(id)}")

    revoke = delete


class AsyncApiKeys(AsyncResource):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[ApiKey]:
        return await self._client.get_page("/v1/api-keys", {"limit": limit, "cursor": cursor})

    async def create(
        self,
        *,
        name: str,
        scopes: Optional[List[str]] = None,
        mode: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> ApiKey:
        body = strip_none({"name": name, "scopes": scopes, "mode": mode, "expires_at": expires_at})
        return cast(ApiKey, await self._client.request("POST", "/v1/api-keys", json=body))

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/api-keys/{seg(id)}")

    revoke = delete
