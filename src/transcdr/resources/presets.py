from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union, cast

from .._base_client import NOT_GIVEN, strip_none, strip_not_given
from .._base_client import path_segment as seg
from ..pagination import AsyncPage, SyncPage
from ..output import check_output
from ..types import OutputOverrides, OutputSpec, Platform, Preset, PresetCategory, PresetVersion
from ._base import AsyncResource, SyncResource

__all__ = ["Presets", "AsyncPresets"]


def _body(
    name: Optional[str],
    output: Optional[OutputSpec],
    slug: Optional[str],
    description: Optional[str],
    metadata: Optional[Dict[str, str]],
    category: Optional[PresetCategory] = None,
    compatibility: Optional[List[Platform]] = None,
    compatibility_notes: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    # Create and replace send a whole spec: check it before it goes.
    check_output(output)
    return strip_none(
        {
            "name": name,
            "slug": slug,
            "description": description,
            "output": output,
            "metadata": metadata,
            "category": category,
            "compatibility": compatibility,
            "compatibility_notes": compatibility_notes,
        }
    )


def _update_body(
    name: Optional[str],
    output: Optional[OutputOverrides],
    slug: Optional[str],
    description: Any,
    metadata: Any,
    category: Any = NOT_GIVEN,
    compatibility: Any = NOT_GIVEN,
    compatibility_notes: Any = NOT_GIVEN,
) -> Dict[str, object]:
    body = strip_none({"name": name, "slug": slug, "output": output})
    body.update(
        strip_not_given(
            {
                "description": description,
                "metadata": metadata,
                "category": category,
                "compatibility": compatibility,
                "compatibility_notes": compatibility_notes,
            }
        )
    )
    return body


def _version_path(id_or_slug: str, version: int) -> str:
    return f"/v1/presets/{seg(id_or_slug)}@{int(version)}"


def _joined(value: Union[str, Sequence[str], None]) -> Optional[str]:
    if value is None or isinstance(value, str):
        return value
    return ",".join(value)


def _list_params(
    limit: Optional[int],
    cursor: Optional[str],
    category: Union[str, Sequence[str], None],
    compatible_with: Union[str, Sequence[str], None],
) -> Dict[str, object]:
    return {
        "limit": limit,
        "cursor": cursor,
        "category": _joined(category),
        "compatible_with": _joined(compatible_with),
    }


class Presets(SyncResource):
    """System presets (``hls-av1-abr``, ``web-av1-1080p``, …) plus your organization's.

    A preset is a whole output spec, versioned: editing its output adds a
    version, and a version never changes. ``create`` and ``replace`` check
    the spec with :func:`~transcdr.validate_output` before sending it."""

    def list(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        category: Union[PresetCategory, Sequence[PresetCategory], None] = None,
        compatible_with: Union[Platform, Sequence[Platform], None] = None,
    ) -> SyncPage[Preset]:
        """``category`` keeps presets in any of the categories given;
        ``compatible_with`` keeps those that play on every platform given.
        Each takes a string or a list."""
        params = _list_params(limit, cursor, category, compatible_with)
        return self._client.get_page("/v1/presets", params)

    def create(
        self,
        *,
        name: str,
        output: OutputSpec,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        category: Optional[PresetCategory] = None,
        compatibility: Optional[List[Platform]] = None,
        compatibility_notes: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Preset:
        body = _body(name, output, slug, description, metadata, category, compatibility, compatibility_notes)
        return cast(Preset, self._client._create("/v1/presets", body, idempotency_key))

    def retrieve(self, id_or_slug: str) -> Preset:
        """A preset by id or slug, at its latest version."""
        return cast(Preset, self._client.request("GET", f"/v1/presets/{seg(id_or_slug)}"))

    def get_version(self, id_or_slug: str, version: int) -> Preset:
        """The preset with ``version`` and ``output`` of version N
        (``GET /v1/presets/{id}@N``)."""
        return cast(Preset, self._client.request("GET", _version_path(id_or_slug, version)))

    def versions(self, id_or_slug: str) -> SyncPage[PresetVersion]:
        """Every version, oldest first: each a whole spec that never changes."""
        return self._client.get_page(f"/v1/presets/{seg(id_or_slug)}/versions")

    def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        output: Optional[OutputOverrides] = None,
        slug: Optional[str] = None,
        description: Optional[str] = NOT_GIVEN,
        metadata: Optional[Dict[str, str]] = NOT_GIVEN,
        category: Optional[PresetCategory] = NOT_GIVEN,
        compatibility: Optional[List[Platform]] = NOT_GIVEN,
        compatibility_notes: Optional[Dict[str, str]] = NOT_GIVEN,
    ) -> Preset:
        """Change the fields given (``PATCH``). ``output`` merges over the
        latest version (objects merge, lists replace, ``None`` removes a
        field); a changed spec is a new version. ``description=None`` or ``metadata=None`` clears it;
        ``category=None``, ``compatibility=None`` or ``compatibility_notes=None``
        derives it from ``output`` again."""
        body = _update_body(
            name, output, slug, description, metadata, category, compatibility, compatibility_notes
        )
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
        category: Optional[PresetCategory] = None,
        compatibility: Optional[List[Platform]] = None,
        compatibility_notes: Optional[Dict[str, str]] = None,
    ) -> Preset:
        """Replace the preset (``PUT``). ``output`` is the whole spec, checked
        as on create; a changed spec is a new version. ``description`` and
        ``metadata`` left out are emptied, ``category``, ``compatibility`` and
        ``compatibility_notes`` left out are derived again; ``slug`` left out
        is kept."""
        body = _body(name, output, slug, description, metadata, category, compatibility, compatibility_notes)
        return cast(Preset, self._client.request("PUT", f"/v1/presets/{seg(id)}", json=body))

    def delete(self, id: str) -> None:
        self._client.request("DELETE", f"/v1/presets/{seg(id)}")


class AsyncPresets(AsyncResource):
    async def list(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        category: Union[PresetCategory, Sequence[PresetCategory], None] = None,
        compatible_with: Union[Platform, Sequence[Platform], None] = None,
    ) -> AsyncPage[Preset]:
        params = _list_params(limit, cursor, category, compatible_with)
        return await self._client.get_page("/v1/presets", params)

    async def create(
        self,
        *,
        name: str,
        output: OutputSpec,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        category: Optional[PresetCategory] = None,
        compatibility: Optional[List[Platform]] = None,
        compatibility_notes: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Preset:
        body = _body(name, output, slug, description, metadata, category, compatibility, compatibility_notes)
        return cast(Preset, await self._client._create("/v1/presets", body, idempotency_key))

    async def retrieve(self, id_or_slug: str) -> Preset:
        return cast(Preset, await self._client.request("GET", f"/v1/presets/{seg(id_or_slug)}"))

    async def get_version(self, id_or_slug: str, version: int) -> Preset:
        return cast(Preset, await self._client.request("GET", _version_path(id_or_slug, version)))

    async def versions(self, id_or_slug: str) -> AsyncPage[PresetVersion]:
        return await self._client.get_page(f"/v1/presets/{seg(id_or_slug)}/versions")

    async def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        output: Optional[OutputOverrides] = None,
        slug: Optional[str] = None,
        description: Optional[str] = NOT_GIVEN,
        metadata: Optional[Dict[str, str]] = NOT_GIVEN,
        category: Optional[PresetCategory] = NOT_GIVEN,
        compatibility: Optional[List[Platform]] = NOT_GIVEN,
        compatibility_notes: Optional[Dict[str, str]] = NOT_GIVEN,
    ) -> Preset:
        body = _update_body(
            name, output, slug, description, metadata, category, compatibility, compatibility_notes
        )
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
        category: Optional[PresetCategory] = None,
        compatibility: Optional[List[Platform]] = None,
        compatibility_notes: Optional[Dict[str, str]] = None,
    ) -> Preset:
        body = _body(name, output, slug, description, metadata, category, compatibility, compatibility_notes)
        return cast(Preset, await self._client.request("PUT", f"/v1/presets/{seg(id)}", json=body))

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/presets/{seg(id)}")
