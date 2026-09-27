"""The platform operator console: ``/v1/admin``.

Every route answers 404 to anyone who is not a platform operator signed in with
a session token."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, Mapping, Optional, cast

from .._base_client import NOT_GIVEN, strip_none, strip_not_given
from .._base_client import path_segment as seg
from ..pagination import AsyncPage, SyncPage
from ..types import AdminJob, AdminOverview, Announcement, Billing, Incident, IncidentDetector, Organization
from ._base import AsyncResource, SyncResource

__all__ = [
    "Admin",
    "AdminAnnouncements",
    "AdminIncidents",
    "AsyncAdmin",
    "AsyncAdminAnnouncements",
    "AsyncAdminIncidents",
]


def _iso(value: Any) -> Any:
    """Send ``datetime`` values as RFC 3339 strings."""
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=_dt.timezone.utc)
        return value.isoformat()
    return value


def _credit_body(
    amount_cents: int, description: Optional[str], expires_in_days: Optional[int]
) -> Dict[str, Any]:
    return strip_none(
        {"amount_cents": amount_cents, "description": description, "expires_in_days": expires_in_days}
    )


def _announcement_body(
    title: Any, body: Any, link: Any, tags: Any, published_at: Any
) -> Dict[str, Any]:
    return strip_not_given(
        {"title": title, "body": body, "link": link, "tags": tags, "published_at": _iso(published_at)}
    )


def _incident_body(
    title: str,
    description: str,
    window_start: Any,
    window_end: Any,
    detector: Optional[str],
    filters: Optional[Mapping[str, Any]],
    multiplier: Optional[int],
) -> Dict[str, Any]:
    return strip_none(
        {
            "title": title,
            "description": description,
            "window_start": _iso(window_start),
            "window_end": _iso(window_end),
            "detector": detector,
            "filters": dict(filters) if filters is not None else None,
            "multiplier": multiplier,
        }
    )


# --------------------------------------------------------------------------
# Sync
# --------------------------------------------------------------------------


class AdminAnnouncements(SyncResource):
    """Changelog entries, as the operator console writes them."""

    def list(self, *, limit: Optional[int] = None, cursor: Optional[str] = None) -> SyncPage[Announcement]:
        """Every announcement, including drafts (``published_at: None``) and service credits."""
        return self._client.get_page("/v1/admin/announcements", {"limit": limit, "cursor": cursor})

    def create(
        self,
        *,
        title: str,
        body: str,
        link: Any = NOT_GIVEN,
        tags: Any = NOT_GIVEN,
        published_at: Any = NOT_GIVEN,
    ) -> Announcement:
        """A changelog entry. ``published_at`` defaults to now; ``None`` saves a
        draft; a future time schedules it. ``link`` is ``{"label", "url"}``."""
        payload = _announcement_body(title, body, link, tags, published_at)
        return cast(Announcement, self._client.request("POST", "/v1/admin/announcements", json=payload))

    def update(
        self,
        id: str,
        *,
        title: Any = NOT_GIVEN,
        body: Any = NOT_GIVEN,
        link: Any = NOT_GIVEN,
        tags: Any = NOT_GIVEN,
        published_at: Any = NOT_GIVEN,
    ) -> Announcement:
        """Changelog entries only. ``published_at=None`` takes one back to a
        draft; ``link=None`` removes the link."""
        payload = _announcement_body(title, body, link, tags, published_at)
        return cast(
            Announcement,
            self._client.request("PATCH", f"/v1/admin/announcements/{seg(id)}", json=payload),
        )

    def delete(self, id: str) -> None:
        """Changelog entries only."""
        self._client.request("DELETE", f"/v1/admin/announcements/{seg(id)}")


class AdminIncidents(SyncResource):
    """Service incidents: find the jobs a defect affected and credit them."""

    def detectors(self) -> SyncPage[IncidentDetector]:
        """The known-defect detectors an incident can use."""
        return self._client.get_page("/v1/admin/incident-detectors")

    def list(self) -> SyncPage[Incident]:
        """The latest 100 incidents."""
        return self._client.get_page("/v1/admin/incidents")

    def create(
        self,
        *,
        title: str,
        description: str,
        window_start: Any,
        window_end: Any = None,
        detector: Optional[str] = None,
        filters: Optional[Mapping[str, Any]] = None,
        multiplier: Optional[int] = None,
    ) -> Incident:
        """Open a draft; nothing is credited until it is previewed and applied.
        ``description`` is what customers are told; ``multiplier`` is 1 to 20."""
        payload = _incident_body(title, description, window_start, window_end, detector, filters, multiplier)
        return cast(Incident, self._client.request("POST", "/v1/admin/incidents", json=payload))

    def retrieve(self, id: str) -> Incident:
        """An incident with every impact."""
        return cast(Incident, self._client.request("GET", f"/v1/admin/incidents/{seg(id)}"))

    def preview(self, id: str) -> Incident:
        """Find the affected jobs; credits nothing."""
        return cast(Incident, self._client.request("POST", f"/v1/admin/incidents/{seg(id)}/preview"))

    def apply(self, id: str, *, include_review: bool = False) -> Incident:
        """Credit each affected organization once; ``include_review`` also
        credits the jobs flagged for review."""
        return cast(
            Incident,
            self._client.request(
                "POST", f"/v1/admin/incidents/{seg(id)}/apply", json={"include_review": include_review}
            ),
        )


class Admin(SyncResource):
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        super().__init__(client)
        self.announcements = AdminAnnouncements(client)
        self.incidents = AdminIncidents(client)

    def overview(self) -> AdminOverview:
        return cast(AdminOverview, self._client.request("GET", "/v1/admin/overview"))

    def jobs(
        self, *, status: Optional[str] = None, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> SyncPage[AdminJob]:
        """Recent jobs across every organization."""
        return self._client.get_page("/v1/admin/jobs", {"status": status, "limit": limit, "cursor": cursor})

    def organizations(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> SyncPage[Organization]:
        return self._client.get_page("/v1/admin/organizations", {"limit": limit, "cursor": cursor})

    def update_organization(
        self, id: str, *, plan: Optional[str] = None, suspended: Optional[bool] = None
    ) -> Organization:
        """Change an organization's plan, or suspend it."""
        return cast(
            Organization,
            self._client.request(
                "PATCH",
                f"/v1/admin/organizations/{seg(id)}",
                json=strip_none({"plan": plan, "suspended": suspended}),
            ),
        )

    def grant_credit(
        self,
        organization_id: str,
        *,
        amount_cents: int,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> Billing:
        """Add (or, negative, remove) credit; returns the organization's billing
        summary. With ``expires_in_days`` a grant is promotional credit that expires."""
        return cast(
            Billing,
            self._client.request(
                "POST",
                f"/v1/admin/organizations/{seg(organization_id)}/credit",
                json=_credit_body(amount_cents, description, expires_in_days),
            ),
        )


# --------------------------------------------------------------------------
# Async
# --------------------------------------------------------------------------


class AsyncAdminAnnouncements(AsyncResource):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[Announcement]:
        return await self._client.get_page("/v1/admin/announcements", {"limit": limit, "cursor": cursor})

    async def create(
        self,
        *,
        title: str,
        body: str,
        link: Any = NOT_GIVEN,
        tags: Any = NOT_GIVEN,
        published_at: Any = NOT_GIVEN,
    ) -> Announcement:
        payload = _announcement_body(title, body, link, tags, published_at)
        return cast(
            Announcement, await self._client.request("POST", "/v1/admin/announcements", json=payload)
        )

    async def update(
        self,
        id: str,
        *,
        title: Any = NOT_GIVEN,
        body: Any = NOT_GIVEN,
        link: Any = NOT_GIVEN,
        tags: Any = NOT_GIVEN,
        published_at: Any = NOT_GIVEN,
    ) -> Announcement:
        payload = _announcement_body(title, body, link, tags, published_at)
        return cast(
            Announcement,
            await self._client.request("PATCH", f"/v1/admin/announcements/{seg(id)}", json=payload),
        )

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/admin/announcements/{seg(id)}")


class AsyncAdminIncidents(AsyncResource):
    async def detectors(self) -> AsyncPage[IncidentDetector]:
        return await self._client.get_page("/v1/admin/incident-detectors")

    async def list(self) -> AsyncPage[Incident]:
        return await self._client.get_page("/v1/admin/incidents")

    async def create(
        self,
        *,
        title: str,
        description: str,
        window_start: Any,
        window_end: Any = None,
        detector: Optional[str] = None,
        filters: Optional[Mapping[str, Any]] = None,
        multiplier: Optional[int] = None,
    ) -> Incident:
        payload = _incident_body(title, description, window_start, window_end, detector, filters, multiplier)
        return cast(Incident, await self._client.request("POST", "/v1/admin/incidents", json=payload))

    async def retrieve(self, id: str) -> Incident:
        return cast(Incident, await self._client.request("GET", f"/v1/admin/incidents/{seg(id)}"))

    async def preview(self, id: str) -> Incident:
        return cast(
            Incident, await self._client.request("POST", f"/v1/admin/incidents/{seg(id)}/preview")
        )

    async def apply(self, id: str, *, include_review: bool = False) -> Incident:
        return cast(
            Incident,
            await self._client.request(
                "POST", f"/v1/admin/incidents/{seg(id)}/apply", json={"include_review": include_review}
            ),
        )


class AsyncAdmin(AsyncResource):
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        super().__init__(client)
        self.announcements = AsyncAdminAnnouncements(client)
        self.incidents = AsyncAdminIncidents(client)

    async def overview(self) -> AdminOverview:
        return cast(AdminOverview, await self._client.request("GET", "/v1/admin/overview"))

    async def jobs(
        self, *, status: Optional[str] = None, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[AdminJob]:
        return await self._client.get_page(
            "/v1/admin/jobs", {"status": status, "limit": limit, "cursor": cursor}
        )

    async def organizations(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[Organization]:
        return await self._client.get_page("/v1/admin/organizations", {"limit": limit, "cursor": cursor})

    async def update_organization(
        self, id: str, *, plan: Optional[str] = None, suspended: Optional[bool] = None
    ) -> Organization:
        return cast(
            Organization,
            await self._client.request(
                "PATCH",
                f"/v1/admin/organizations/{seg(id)}",
                json=strip_none({"plan": plan, "suspended": suspended}),
            ),
        )

    async def grant_credit(
        self,
        organization_id: str,
        *,
        amount_cents: int,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> Billing:
        return cast(
            Billing,
            await self._client.request(
                "POST",
                f"/v1/admin/organizations/{seg(organization_id)}/credit",
                json=_credit_body(amount_cents, description, expires_in_days),
            ),
        )

