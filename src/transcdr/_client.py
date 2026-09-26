from __future__ import annotations

from typing import Any, Mapping, Optional

import httpx

from ._base_client import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    AsyncAPIClient,
    SyncAPIClient,
    Timeout,
)
from .resources.api_keys import ApiKeys, AsyncApiKeys
from .resources.assets import Assets, AsyncAssets
from .resources.auth import AsyncAuth, Auth
from .resources.automations import AsyncAutomations, Automations
from .resources.connections import AsyncConnections, Connections
from .resources.jobs import AsyncDeliveries, AsyncJobs, Deliveries, Jobs
from .resources.misc import (
    AsyncBillingResource,
    AsyncCapabilitiesResource,
    AsyncEvents,
    AsyncPlans,
    AsyncProbe,
    AsyncStatsResource,
    AsyncStatusResource,
    AsyncUsageResource,
    BillingResource,
    CapabilitiesResource,
    Events,
    Plans,
    Probe,
    StatsResource,
    StatusResource,
    UsageResource,
)
from .resources.organization import AsyncOrganizationResource, OrganizationResource
from .resources.presets import AsyncPresets, Presets
from .resources.uploads import AsyncUploads, Uploads
from .resources.webhooks import AsyncWebhooks, Webhooks

__all__ = ["Transcdr", "AsyncTranscdr"]

_UNSET: Any = object()


class Transcdr(SyncAPIClient):
    """The Transcdr API client.

    ::

        client = Transcdr(api_key="tdk_live_...")  # or set TRANSCDR_API_KEY
        job = client.jobs.create(input="https://example.com/in.mp4", preset="hls-av1-abr")

    ``api_key`` defaults to ``$TRANSCDR_API_KEY`` and ``base_url`` to
    ``$TRANSCDR_BASE_URL`` or ``https://api.transcdr.io``. GET/PUT/DELETE
    requests and POSTs carrying an ``Idempotency-Key`` are retried up to
    ``max_retries`` times on connection errors, 408, 429 and 5xx.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            http_client=http_client,
        )
        self.auth = Auth(self)
        self.organization = OrganizationResource(self)
        self.api_keys = ApiKeys(self)
        self.uploads = Uploads(self)
        self.assets = Assets(self)
        self.jobs = Jobs(self)
        self.deliveries = Deliveries(self)
        self.probe = Probe(self)
        self.presets = Presets(self)
        self.webhooks = Webhooks(self)
        self.connections = Connections(self)
        self.automations = Automations(self)
        self.events = Events(self)
        self.usage = UsageResource(self)
        self.billing = BillingResource(self)
        self.plans = Plans(self)
        self.capabilities = CapabilitiesResource(self)
        self.status = StatusResource(self)
        self.stats = StatsResource(self)

    def with_options(
        self,
        *,
        api_key: Optional[str] = _UNSET,
        base_url: Optional[str] = _UNSET,
        timeout: Timeout = _UNSET,
        max_retries: int = _UNSET,
        default_headers: Optional[Mapping[str, str]] = _UNSET,
    ) -> "Transcdr":
        """A copy of this client with some settings changed, sharing its connection pool::

            client.with_options(max_retries=5, timeout=120).jobs.list()
        """
        copy = Transcdr(
            api_key=self.api_key if api_key is _UNSET else api_key,
            base_url=self.base_url if base_url is _UNSET else base_url,
            timeout=self.timeout if timeout is _UNSET else timeout,
            max_retries=self.max_retries if max_retries is _UNSET else max_retries,
            default_headers=self.default_headers if default_headers is _UNSET else default_headers,
            http_client=self._client,
        )
        copy._sleep = self._sleep  # type: ignore[method-assign]
        return copy


class AsyncTranscdr(AsyncAPIClient):
    """The asyncio flavour of :class:`Transcdr`; every method is awaitable::

        async with AsyncTranscdr() as client:
            job = await client.jobs.create(input=url, preset="hls-av1-abr")
            job = await client.jobs.wait(job["id"])
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            http_client=http_client,
        )
        self.auth = AsyncAuth(self)
        self.organization = AsyncOrganizationResource(self)
        self.api_keys = AsyncApiKeys(self)
        self.uploads = AsyncUploads(self)
        self.assets = AsyncAssets(self)
        self.jobs = AsyncJobs(self)
        self.deliveries = AsyncDeliveries(self)
        self.probe = AsyncProbe(self)
        self.presets = AsyncPresets(self)
        self.webhooks = AsyncWebhooks(self)
        self.connections = AsyncConnections(self)
        self.automations = AsyncAutomations(self)
        self.events = AsyncEvents(self)
        self.usage = AsyncUsageResource(self)
        self.billing = AsyncBillingResource(self)
        self.plans = AsyncPlans(self)
        self.capabilities = AsyncCapabilitiesResource(self)
        self.status = AsyncStatusResource(self)
        self.stats = AsyncStatsResource(self)

    def with_options(
        self,
        *,
        api_key: Optional[str] = _UNSET,
        base_url: Optional[str] = _UNSET,
        timeout: Timeout = _UNSET,
        max_retries: int = _UNSET,
        default_headers: Optional[Mapping[str, str]] = _UNSET,
    ) -> "AsyncTranscdr":
        copy = AsyncTranscdr(
            api_key=self.api_key if api_key is _UNSET else api_key,
            base_url=self.base_url if base_url is _UNSET else base_url,
            timeout=self.timeout if timeout is _UNSET else timeout,
            max_retries=self.max_retries if max_retries is _UNSET else max_retries,
            default_headers=self.default_headers if default_headers is _UNSET else default_headers,
            http_client=self._client,
        )
        copy._sleep = self._sleep  # type: ignore[method-assign]
        return copy
