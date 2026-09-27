from __future__ import annotations

from typing import Any, Dict, Optional, cast

from .._base_client import NOT_GIVEN, strip_none, strip_not_given
from .._base_client import path_segment as seg
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


def _update_body(
    name: Optional[str],
    output: Optional[OutputSpec],
    slug: Optional[str],
    description: Any,
    metadata: Any,
) -> Dict[str, object]:
    body = strip_none({"name": name, "slug": slug, "output": output})
    body.update(strip_not_given({"description": description, "metadata": metadata}))
    return body


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
        idempotency_key: Optional[str] = None,
    ) -> Preset:
        body = _body(name, output, slug, description, metadata)
        return cast(Preset, self._client._create("/v1/presets", body, idempotency_key))

    def retrieve(self, id_or_slug: str) -> Preset:
        return cast(Preset, self._client.request("GET", f"/v1/presets/{seg(id_or_slug)}"))

    def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        output: Optional[OutputSpec] = None,
        slug: Optional[str] = None,
        description: Optional[str] = NOT_GIVEN,
        metadata: Optional[Dict[str, str]] = NOT_GIVEN,
    ) -> Preset:
        """Change the fields given (``PATCH``). ``output`` merges into the
        stored spec. ``description=None`` or ``metadata=None`` clears it."""
        body = _update_body(name, output, slug, description, metadata)
        return cast(Preset, self._client.request("PATCH", f"/v1/presets/{seg(id)}", json=body))

    def replace(
        self,
        id: str,
        *,
        name: str,
        output: OutputSpec,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Preset:
        """Replace the preset (``PUT``). ``output`` is the whole spec: a field
        left out takes its default, as on create. ``description`` and
        ``metadata`` left out are emptied; ``slug`` left out is kept."""
        body = _body(name, output, slug, description, metadata)
        return cast(Preset, self._client.request("PUT", f"/v1/presets/{seg(id)}", json=body))

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
        idempotency_key: Optional[str] = None,
    ) -> Preset:
        body = _body(name, output, slug, description, metadata)
        return cast(Preset, await self._client._create("/v1/presets", body, idempotency_key))

    async def retrieve(self, id_or_slug: str) -> Preset:
        return cast(Preset, await self._client.request("GET", f"/v1/presets/{seg(id_or_slug)}"))

    async def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        output: Optional[OutputSpec] = None,
        slug: Optional[str] = None,
        description: Optional[str] = NOT_GIVEN,
        metadata: Optional[Dict[str, str]] = NOT_GIVEN,
    ) -> Preset:
        body = _update_body(name, output, slug, description, metadata)
        return cast(Preset, await self._client.request("PATCH", f"/v1/presets/{seg(id)}", json=body))

    async def replace(
        self,
        id: str,
        *,
        name: str,
        output: OutputSpec,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Preset:
        body = _body(name, output, slug, description, metadata)
        return cast(Preset, await self._client.request("PUT", f"/v1/presets/{seg(id)}", json=body))

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/presets/{seg(id)}")
