"""Announcements (what's new, and service credits) and the public changelog."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..pagination import AsyncPage, SyncPage
from ..types import Announcement
from ._base import AsyncResource, SyncResource

__all__ = ["Announcements", "Changelog", "AsyncAnnouncements", "AsyncChangelog"]


def _list_params(unseen: Optional[bool], kind: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
    return {"unseen": True if unseen else None, "kind": kind, "limit": limit}


class Announcements(SyncResource):
    """What's new, and service credits, for the signed-in user."""

    def list(
        self, *, unseen: Optional[bool] = None, kind: Optional[str] = None, limit: Optional[int] = None
    ) -> SyncPage[Announcement]:
        """Newest first. ``unseen=True`` returns only what this user has not seen
        yet, service credits before changelog entries. ``kind`` is
        ``changelog`` or ``service_credit``."""
        return self._client.get_page("/v1/announcements", _list_params(unseen, kind, limit))

    def mark_seen(self, ids: List[str]) -> None:
        """Remember that this user has seen these announcements (session tokens
        only; idempotent). No ids, no request."""
        if not ids:
            return
        self._client.request("POST", "/v1/announcements/seen", json={"ids": list(ids)})

    def mark_all_seen(self) -> None:
        """Mark everything this user can see as seen (session tokens only)."""
        self._client.request("POST", "/v1/announcements/seen", json={"all": True})


class Changelog(SyncResource):
    """The public changelog; no key needed."""

    def list(self, *, limit: Optional[int] = None, cursor: Optional[str] = None) -> SyncPage[Announcement]:
        """Published changelog entries, newest first."""
        return self._client.get_page("/v1/changelog", {"limit": limit, "cursor": cursor})


class AsyncAnnouncements(AsyncResource):
    async def list(
        self, *, unseen: Optional[bool] = None, kind: Optional[str] = None, limit: Optional[int] = None
    ) -> AsyncPage[Announcement]:
        return await self._client.get_page("/v1/announcements", _list_params(unseen, kind, limit))

    async def mark_seen(self, ids: List[str]) -> None:
        if not ids:
            return
        await self._client.request("POST", "/v1/announcements/seen", json={"ids": list(ids)})

    async def mark_all_seen(self) -> None:
        await self._client.request("POST", "/v1/announcements/seen", json={"all": True})


class AsyncChangelog(AsyncResource):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[Announcement]:
        return await self._client.get_page("/v1/changelog", {"limit": limit, "cursor": cursor})
