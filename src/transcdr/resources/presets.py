from __future__ import annotations

from typing import Dict, Optional, cast

from .._base_client import path_segment as seg
from .._base_client import strip_none
from ..pagination import AsyncPage, SyncPage
from ..types import OutputSpec, Preset
from ._base import AsyncResource, SyncResource

__all__ = ["Presets", "AsyncPresets"]


def _body(
    name: Optional[str],
    output: Optional[OutputSpec],
    slug: Optional[str],
    description: Optional[str],
    metadata: Optional[Dict[str, str]],
) -> Dict[str, object]:
    return strip_none(
        {"name": name, "slug": slug, "description": description, "output": output, "metadata": metadata}
    )


class Presets(SyncResource):
    """System presets (``hls-av1-abr``, ``web-av1-1080p``, …) plus your organization's."""

    def list(self, *, limit: Optional[int] = None, cursor: Optional[str] = None) -> SyncPage[Preset]:
        return self._client.get_page("/v1/presets", {"limit": limit, "cursor": cursor})

    def create(
        self,
        *,
        name: str,
        output: OutputSpec,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Preset:
        body = _body(name, output, slug, description, metadata)
        return cast(Preset, self._client.request("POST", "/v1/presets", json=body))

    def retrieve(self, id_or_slug: str) -> Preset:
        return cast(Preset, self._client.request("GET", f"/v1/presets/{seg(id_or_slug)}"))

    def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        output: Optional[OutputSpec] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Preset:
        body = _body(name, output, slug, description, metadata)
        return cast(Preset, self._client.request("PATCH", f"/v1/presets/{seg(id)}", json=body))

    def delete(self, id: str) -> None:
        self._client.request("DELETE", f"/v1/presets/{seg(id)}")


class AsyncPresets(AsyncResource):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[Preset]:
        return await self._client.get_page("/v1/presets", {"limit": limit, "cursor": cursor})

    async def create(
        self,
        *,
        name: str,
        output: OutputSpec,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Preset:
        body = _body(name, output, slug, description, metadata)
        return cast(Preset, await self._client.request("POST", "/v1/presets", json=body))

    async def retrieve(self, id_or_slug: str) -> Preset:
        return cast(Preset, await self._client.request("GET", f"/v1/presets/{seg(id_or_slug)}"))

    async def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        output: Optional[OutputSpec] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Preset:
        body = _body(name, output, slug, description, metadata)
        return cast(Preset, await self._client.request("PATCH", f"/v1/presets/{seg(id)}", json=body))

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/presets/{seg(id)}")
