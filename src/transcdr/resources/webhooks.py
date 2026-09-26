from __future__ import annotations

from typing import Any, List, Optional, Union, cast

from .. import webhooks as _signature
from .._base_client import path_segment as seg
from .._base_client import strip_none
from ..pagination import AsyncPage, SyncPage
from ..types import Event, WebhookDelivery, WebhookEndpoint
from ._base import AsyncResource, SyncResource

__all__ = ["Webhooks", "AsyncWebhooks"]


class _SignatureHelpers:
    """``client.webhooks.verify_signature`` / ``construct_event`` — the same
    functions as the :mod:`transcdr.webhooks` module, for convenience."""

    @staticmethod
    def verify_signature(
        payload: Union[bytes, str], header: Optional[str], secret: str, tolerance: int = 300
    ) -> bool:
        return _signature.verify_signature(payload, header, secret, tolerance)

    @staticmethod
    def construct_event(
        payload: Union[bytes, str], header: Optional[str], secret: str, tolerance: int = 300
    ) -> Event:
        return _signature.construct_event(payload, header, secret, tolerance)


class Webhooks(SyncResource, _SignatureHelpers):
    def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> SyncPage[WebhookEndpoint]:
        return self._client.get_page("/v1/webhooks", {"limit": limit, "cursor": cursor})

    def create(
        self, *, url: str, events: Optional[List[str]] = None, description: Optional[str] = None
    ) -> WebhookEndpoint:
        """Register an endpoint. The returned ``secret`` is shown only on create and rotate."""
        body = strip_none({"url": url, "events": events, "description": description})
        return cast(WebhookEndpoint, self._client.request("POST", "/v1/webhooks", json=body))

    def retrieve(self, id: str) -> WebhookEndpoint:
        return cast(WebhookEndpoint, self._client.request("GET", f"/v1/webhooks/{seg(id)}"))

    def update(
        self,
        id: str,
        *,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> WebhookEndpoint:
        body = strip_none(
            {"url": url, "events": events, "description": description, "enabled": enabled}
        )
        return cast(
            WebhookEndpoint, self._client.request("PATCH", f"/v1/webhooks/{seg(id)}", json=body)
        )

    def delete(self, id: str) -> None:
        self._client.request("DELETE", f"/v1/webhooks/{seg(id)}")

    def rotate_secret(self, id: str) -> WebhookEndpoint:
        return cast(
            WebhookEndpoint, self._client.request("POST", f"/v1/webhooks/{seg(id)}/rotate-secret")
        )

    def test(self, id: str) -> Any:
        """Send a ``webhook.test`` event to the endpoint."""
        return self._client.request("POST", f"/v1/webhooks/{seg(id)}/test")

    def deliveries(
        self, id: str, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> SyncPage[WebhookDelivery]:
        return self._client.get_page(
            f"/v1/webhooks/{seg(id)}/deliveries", {"limit": limit, "cursor": cursor}
        )

    def redeliver(self, delivery_id: str) -> WebhookDelivery:
        return cast(
            WebhookDelivery,
            self._client.request("POST", f"/v1/webhook-deliveries/{seg(delivery_id)}/redeliver"),
        )


class AsyncWebhooks(AsyncResource, _SignatureHelpers):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[WebhookEndpoint]:
        return await self._client.get_page("/v1/webhooks", {"limit": limit, "cursor": cursor})

    async def create(
        self, *, url: str, events: Optional[List[str]] = None, description: Optional[str] = None
    ) -> WebhookEndpoint:
        body = strip_none({"url": url, "events": events, "description": description})
        return cast(WebhookEndpoint, await self._client.request("POST", "/v1/webhooks", json=body))

    async def retrieve(self, id: str) -> WebhookEndpoint:
        return cast(WebhookEndpoint, await self._client.request("GET", f"/v1/webhooks/{seg(id)}"))

    async def update(
        self,
        id: str,
        *,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> WebhookEndpoint:
        body = strip_none(
            {"url": url, "events": events, "description": description, "enabled": enabled}
        )
        return cast(
            WebhookEndpoint,
            await self._client.request("PATCH", f"/v1/webhooks/{seg(id)}", json=body),
        )

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/webhooks/{seg(id)}")

    async def rotate_secret(self, id: str) -> WebhookEndpoint:
        return cast(
            WebhookEndpoint,
            await self._client.request("POST", f"/v1/webhooks/{seg(id)}/rotate-secret"),
        )

    async def test(self, id: str) -> Any:
        return await self._client.request("POST", f"/v1/webhooks/{seg(id)}/test")

    async def deliveries(
        self, id: str, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[WebhookDelivery]:
        return await self._client.get_page(
            f"/v1/webhooks/{seg(id)}/deliveries", {"limit": limit, "cursor": cursor}
        )

    async def redeliver(self, delivery_id: str) -> WebhookDelivery:
        return cast(
            WebhookDelivery,
            await self._client.request(
                "POST", f"/v1/webhook-deliveries/{seg(delivery_id)}/redeliver"
            ),
        )
