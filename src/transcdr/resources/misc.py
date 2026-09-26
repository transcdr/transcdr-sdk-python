"""Probe, events, usage, billing, plans, capabilities, status and stats."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Union, cast

from .._base_client import path_segment as seg
from ..pagination import AsyncPage, SyncPage
from ..types import Billing, Capabilities, Event, Invoice, Job, Plan, Stats, Status, Usage
from ._base import AsyncResource, SyncResource, coerce_input

__all__ = [
    "Probe",
    "Events",
    "UsageResource",
    "BillingResource",
    "Invoices",
    "Plans",
    "CapabilitiesResource",
    "StatusResource",
    "StatsResource",
    "AsyncProbe",
    "AsyncEvents",
    "AsyncUsageResource",
    "AsyncBillingResource",
    "AsyncInvoices",
    "AsyncPlans",
    "AsyncCapabilitiesResource",
    "AsyncStatusResource",
    "AsyncStatsResource",
]

# ``?wait=true`` blocks up to 60 s server-side.
_PROBE_WAIT_TIMEOUT = 90.0


def _probe_timeout(client_timeout: Any, wait: bool) -> Any:
    if not wait:
        return None
    if isinstance(client_timeout, (int, float)):
        return max(float(client_timeout), _PROBE_WAIT_TIMEOUT)
    return _PROBE_WAIT_TIMEOUT if client_timeout is not None else None


def _usage_params(from_: Any, to: Any, granularity: Optional[str]) -> Mapping[str, Any]:
    return {"from": from_, "to": to, "granularity": granularity}


# --------------------------------------------------------------------------
# Sync
# --------------------------------------------------------------------------


class Probe(SyncResource):
    def create(self, *, input: Union[str, Mapping[str, Any]], wait: bool = False) -> Job:
        """Probe an input without transcoding (a ``kind: probe`` job).

        With ``wait=True`` the call blocks up to 60 s and the job's
        ``input_info`` holds the :class:`~transcdr.types.MediaInfo`."""
        return cast(
            Job,
            self._client.request(
                "POST",
                "/v1/probe",
                json={"input": coerce_input(input)},
                params={"wait": True} if wait else None,
                timeout=_probe_timeout(self._client.timeout, wait),
            ),
        )


class Events(SyncResource):
    def list(
        self, *, type: Optional[str] = None, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> SyncPage[Event]:
        return self._client.get_page("/v1/events", {"type": type, "limit": limit, "cursor": cursor})

    def retrieve(self, id: str) -> Event:
        return cast(Event, self._client.request("GET", f"/v1/events/{seg(id)}"))


class UsageResource(SyncResource):
    def retrieve(
        self, *, from_: Any = None, to: Any = None, granularity: Optional[str] = None
    ) -> Usage:
        """``from_``/``to`` are dates (``date`` objects or ``"2026-09-01"``);
        ``granularity`` is ``day`` | ``week`` | ``month``."""
        return cast(
            Usage, self._client.request("GET", "/v1/usage", params=_usage_params(from_, to, granularity))
        )


class Invoices(SyncResource):
    def list(self, *, limit: Optional[int] = None, cursor: Optional[str] = None) -> SyncPage[Invoice]:
        return self._client.get_page("/v1/billing/invoices", {"limit": limit, "cursor": cursor})


class BillingResource(SyncResource):
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        super().__init__(client)
        self.invoices = Invoices(client)

    def retrieve(self) -> Billing:
        return cast(Billing, self._client.request("GET", "/v1/billing"))

    def change_plan(self, plan: str) -> Billing:
        """Switch plan (owner only): ``free`` | ``starter`` | ``pro`` | ``enterprise``."""
        return cast(Billing, self._client.request("PUT", "/v1/billing/plan", json={"plan": plan}))


class Plans(SyncResource):
    def list(self) -> SyncPage[Plan]:
        return self._client.get_page("/v1/plans")


class CapabilitiesResource(SyncResource):
    def retrieve(self) -> Capabilities:
        return cast(Capabilities, self._client.request("GET", "/v1/capabilities"))


class StatusResource(SyncResource):
    def retrieve(self) -> Status:
        return cast(Status, self._client.request("GET", "/v1/status"))


class StatsResource(SyncResource):
    def retrieve(self) -> Stats:
        """Public platform statistics: totals, the last 24 h and a daily series."""
        return cast(Stats, self._client.request("GET", "/v1/stats"))


# --------------------------------------------------------------------------
# Async
# --------------------------------------------------------------------------


class AsyncProbe(AsyncResource):
    async def create(self, *, input: Union[str, Mapping[str, Any]], wait: bool = False) -> Job:
        return cast(
            Job,
            await self._client.request(
                "POST",
                "/v1/probe",
                json={"input": coerce_input(input)},
                params={"wait": True} if wait else None,
                timeout=_probe_timeout(self._client.timeout, wait),
            ),
        )


class AsyncEvents(AsyncResource):
    async def list(
        self, *, type: Optional[str] = None, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[Event]:
        return await self._client.get_page(
            "/v1/events", {"type": type, "limit": limit, "cursor": cursor}
        )

    async def retrieve(self, id: str) -> Event:
        return cast(Event, await self._client.request("GET", f"/v1/events/{seg(id)}"))


class AsyncUsageResource(AsyncResource):
    async def retrieve(
        self, *, from_: Any = None, to: Any = None, granularity: Optional[str] = None
    ) -> Usage:
        return cast(
            Usage,
            await self._client.request(
                "GET", "/v1/usage", params=_usage_params(from_, to, granularity)
            ),
        )


class AsyncInvoices(AsyncResource):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[Invoice]:
        return await self._client.get_page(
            "/v1/billing/invoices", {"limit": limit, "cursor": cursor}
        )


class AsyncBillingResource(AsyncResource):
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        super().__init__(client)
        self.invoices = AsyncInvoices(client)

    async def retrieve(self) -> Billing:
        return cast(Billing, await self._client.request("GET", "/v1/billing"))

    async def change_plan(self, plan: str) -> Billing:
        return cast(
            Billing, await self._client.request("PUT", "/v1/billing/plan", json={"plan": plan})
        )


class AsyncPlans(AsyncResource):
    async def list(self) -> AsyncPage[Plan]:
        return await self._client.get_page("/v1/plans")


class AsyncCapabilitiesResource(AsyncResource):
    async def retrieve(self) -> Capabilities:
        return cast(Capabilities, await self._client.request("GET", "/v1/capabilities"))


class AsyncStatusResource(AsyncResource):
    async def retrieve(self) -> Status:
        return cast(Status, await self._client.request("GET", "/v1/status"))


class AsyncStatsResource(AsyncResource):
    async def retrieve(self) -> Stats:
        return cast(Stats, await self._client.request("GET", "/v1/stats"))
