from __future__ import annotations

from typing import Dict, Optional, cast

from .._base_client import path_segment as seg
from .._base_client import strip_none
from ..pagination import AsyncPage, SyncPage
from ..types import Asset
from ._base import AsyncResource, SyncResource

__all__ = ["Assets", "AsyncAssets"]


class Assets(SyncResource):
    """Source files. Upload local files with ``client.uploads.upload_file``."""

    def list(self, *, limit: Optional[int] = None, cursor: Optional[str] = None) -> SyncPage[Asset]:
        return self._client.get_page("/v1/assets", {"limit": limit, "cursor": cursor})

    def create(
        self,
        *,
        url: str,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Asset:
        """Link a remote file by URL; jobs read the URL directly."""
        body = strip_none({"url": url, "filename": filename, "metadata": metadata})
        return cast(Asset, self._client.request("POST", "/v1/assets", json=body))

    def retrieve(self, id: str) -> Asset:
        return cast(Asset, self._client.request("GET", f"/v1/assets/{seg(id)}"))

    def delete(self, id: str) -> None:
        self._client.request("DELETE", f"/v1/assets/{seg(id)}")

    def download_url(self, id: str) -> str:
        """A short-lived signed URL for the asset's bytes."""
        resp = self._client.request("GET", f"/v1/assets/{seg(id)}/content")
        return cast(str, resp["url"])


class AsyncAssets(AsyncResource):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[Asset]:
        return await self._client.get_page("/v1/assets", {"limit": limit, "cursor": cursor})

    async def create(
        self,
        *,
        url: str,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Asset:
        body = strip_none({"url": url, "filename": filename, "metadata": metadata})
        return cast(Asset, await self._client.request("POST", "/v1/assets", json=body))

    async def retrieve(self, id: str) -> Asset:
        return cast(Asset, await self._client.request("GET", f"/v1/assets/{seg(id)}"))

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/assets/{seg(id)}")

    async def download_url(self, id: str) -> str:
        resp = await self._client.request("GET", f"/v1/assets/{seg(id)}/content")
        return cast(str, resp["url"])
