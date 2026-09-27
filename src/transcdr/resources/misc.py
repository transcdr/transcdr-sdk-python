"""Probe, events, usage, billing, plans, capabilities, status and stats."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Union, cast

from .._base_client import NOT_GIVEN
from .._base_client import new_idempotency_key
from .._base_client import path_segment as seg
from ..pagination import AsyncPage, SyncPage
from ..types import (
    Billing,
    Capabilities,
    Checkout,
    CreditTransaction,
    Event,
    InputReport,
    Job,
    Plan,
    Portal,
    Statement,
    Stats,
    Status,
    Usage,
)
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




def _checkout_body(plan: Optional[str], credit_cents: Optional[int]) -> Dict[str, Any]:
    if (plan is None) == (credit_cents is None):
        raise ValueError("pass exactly one of plan or credit_cents")
    return {"plan": plan} if plan is not None else {"credit_cents": credit_cents}


def _settings_body(monthly_limit_cents: Any, auto_recharge: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if monthly_limit_cents is not NOT_GIVEN:
        body["monthly_limit_cents"] = monthly_limit_cents
    if auto_recharge is not None:
        body["auto_recharge"] = dict(auto_recharge)
    return body


def _probe_timeout(client_timeout: Any, wait: bool) -> Any:
    if not wait:
        return None
    if isinstance(client_timeout, (int, float)):
        return max(float(client_timeout), _PROBE_WAIT_TIMEOUT)
    return _PROBE_WAIT_TIMEOUT if client_timeout is not None else None


def _usage_params(from_: Any, to: Any, granularity: Optional[str]) -> Mapping[str, Any]:
    return {"from": from_, "to": to, "granularity": granularity}


def _inputs_params(from_: Any, to: Any) -> Mapping[str, Any]:
    return {"from": from_, "to": to}


# --------------------------------------------------------------------------
# Sync
# --------------------------------------------------------------------------


class Probe(SyncResource):
    def create(
        self,
        *,
        input: Union[str, Mapping[str, Any]],
        wait: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Job:
        """Probe an input without transcoding (a ``kind: probe`` job).

        With ``wait=True`` the call blocks up to 60 s and the job's
        ``input_info`` holds the :class:`~transcdr.types.MediaInfo`."""
        return cast(
            Job,
            self._client.request(
                "POST",
                "/v1/probe",
                json={"input": coerce_input(input)},
                idempotency_key=idempotency_key or new_idempotency_key(),
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

    def inputs(self, *, from_: Any = None, to: Any = None) -> InputReport:
        """The inputs the range's jobs read, bucketed by duration, size and kind
        (``container/codec``), for a duration × size chart. ``from_`` defaults
        to 29 days before ``to``, and ``to`` to today."""
        return cast(
            InputReport, self._client.request("GET", "/v1/usage/inputs", params=_inputs_params(from_, to))
        )


class Invoices(SyncResource):
    """Monthly statements: credit added and the usage drawn from it."""

    def list(self, *, limit: Optional[int] = None, cursor: Optional[str] = None) -> SyncPage[Statement]:
        return self._client.get_page("/v1/billing/invoices", {"limit": limit, "cursor": cursor})


class BillingResource(SyncResource):
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        super().__init__(client)
        self.invoices = Invoices(client)

    def retrieve(self) -> Billing:
        """The plan, credit balance, spending controls and this month's usage."""
        return cast(Billing, self._client.request("GET", "/v1/billing"))

    def checkout(self, *, plan: Optional[str] = None, credit_cents: Optional[int] = None) -> Checkout:
        """Subscribe (``plan="growth"``) or buy credit (``credit_cents=5000``,
        $10 to $10,000). Redirect the customer to ``url`` when it is not
        ``None``; an existing subscription changes plan in place
        (``changed=True``). Owner only."""
        return cast(
            Checkout, self._client.request("POST", "/v1/billing/checkout", json=_checkout_body(plan, credit_cents))
        )

    def portal(self) -> Portal:
        """A link to the payment portal: cards, receipts, cancelling. Owner only."""
        return cast(Portal, self._client.request("POST", "/v1/billing/portal", json={}))

    def update_settings(
        self,
        *,
        monthly_limit_cents: Any = NOT_GIVEN,
        auto_recharge: Optional[Mapping[str, Any]] = None,
    ) -> Billing:
        """Spending controls (owner only). ``monthly_limit_cents=None`` clears
        the limit; ``auto_recharge={"enabled": True, "threshold_cents": 1000,
        "amount_cents": 5000, "monthly_cap_cents": 20000}``."""
        return cast(
            Billing,
            self._client.request(
                "PUT", "/v1/billing/settings", json=_settings_body(monthly_limit_cents, auto_recharge)
            ),
        )

    def transactions(self, *, limit: Optional[int] = None) -> SyncPage[CreditTransaction]:
        """The credit ledger, newest first (``limit`` 1 to 200, default 50)."""
        return self._client.get_page("/v1/billing/transactions", {"limit": limit})

    def change_plan(self, plan: str) -> Billing:
        """Move an existing subscription to ``starter`` | ``growth`` | ``scale``
        (owner only). A first subscription goes through :meth:`checkout`."""
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
    async def create(
        self,
        *,
        input: Union[str, Mapping[str, Any]],
        wait: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Job:
        return cast(
            Job,
            await self._client.request(
                "POST",
                "/v1/probe",
                json={"input": coerce_input(input)},
                idempotency_key=idempotency_key or new_idempotency_key(),
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

    async def inputs(self, *, from_: Any = None, to: Any = None) -> InputReport:
        return cast(
            InputReport,
            await self._client.request("GET", "/v1/usage/inputs", params=_inputs_params(from_, to)),
        )


class AsyncInvoices(AsyncResource):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[Statement]:
        return await self._client.get_page(
            "/v1/billing/invoices", {"limit": limit, "cursor": cursor}
        )


class AsyncBillingResource(AsyncResource):
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        super().__init__(client)
        self.invoices = AsyncInvoices(client)

    async def retrieve(self) -> Billing:
        return cast(Billing, await self._client.request("GET", "/v1/billing"))

    async def checkout(self, *, plan: Optional[str] = None, credit_cents: Optional[int] = None) -> Checkout:
        return cast(
            Checkout,
            await self._client.request("POST", "/v1/billing/checkout", json=_checkout_body(plan, credit_cents)),
        )

    async def portal(self) -> Portal:
        return cast(Portal, await self._client.request("POST", "/v1/billing/portal", json={}))

    async def update_settings(
        self,
        *,
        monthly_limit_cents: Any = NOT_GIVEN,
        auto_recharge: Optional[Mapping[str, Any]] = None,
    ) -> Billing:
        return cast(
            Billing,
            await self._client.request(
                "PUT", "/v1/billing/settings", json=_settings_body(monthly_limit_cents, auto_recharge)
            ),
        )

    async def transactions(self, *, limit: Optional[int] = None) -> AsyncPage[CreditTransaction]:
        return await self._client.get_page("/v1/billing/transactions", {"limit": limit})

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
