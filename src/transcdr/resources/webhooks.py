from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Union, cast

from .. import webhooks as _signature
from .._base_client import path_segment as seg
from .._base_client import strip_none
from ..pagination import AsyncPage, SyncPage
from ..types import Event, WebhookCheck, WebhookDelivery, WebhookEndpoint
from ._base import AsyncResource, SyncResource

__all__ = ["Webhooks", "AsyncWebhooks"]


def _create_body(
    url: Optional[str],
    type: Optional[str],
    topic_arn: Optional[str],
    queue_url: Optional[str],
    aws: Optional[Mapping[str, Any]],
    connection_id: Optional[str],
    events: Optional[List[str]],
    description: Optional[str],
) -> Dict[str, Any]:
    targets = [v for v in (url, topic_arn, queue_url, connection_id) if v is not None]
    if len(targets) != 1:
        raise TypeError("pass exactly one of url=, topic_arn=, queue_url= or connection_id=")
    if type is None:
        type = "sns" if topic_arn is not None else "sqs" if queue_url is not None else None
    return strip_none(
        {
            "type": type,
            "url": url,
            "topic_arn": topic_arn,
            "queue_url": queue_url,
            # Kept as given: None inside aws is sent as null.
            "aws": dict(aws) if aws is not None else None,
            "connection_id": connection_id,
            "events": events,
            "description": description,
        }
    )


def _update_body(
    url: Optional[str],
    topic_arn: Optional[str],
    queue_url: Optional[str],
    aws: Optional[Mapping[str, Any]],
    events: Optional[List[str]],
    description: Optional[str],
    enabled: Optional[bool],
) -> Dict[str, Any]:
    return strip_none(
        {
            "url": url,
            "topic_arn": topic_arn,
            "queue_url": queue_url,
            "aws": dict(aws) if aws is not None else None,
            "events": events,
            "description": description,
            "enabled": enabled,
        }
    )


class _SignatureHelpers:
    """``client.webhooks.verify_signature`` / ``construct_event`` /
    ``verify_sns_sqs_signature``: the same functions as the
    :mod:`transcdr.webhooks` module, for convenience."""

    @staticmethod
    def verify_signature(
        payload: Union[bytes, str], header: Optional[str], secret: str, tolerance: int = 300
    ) -> bool:
        return _signature.verify_signature(payload, header, secret, tolerance)

    @staticmethod
    def verify_sns_sqs_signature(
        message: Union[bytes, str], attributes: Any, secret: str, tolerance: int = 300
    ) -> bool:
        return _signature.verify_sns_sqs_signature(message, attributes, secret, tolerance)

    @staticmethod
    def construct_event(
        payload: Union[bytes, str], header: Optional[str], secret: str, tolerance: int = 300
    ) -> Event:
        return _signature.construct_event(payload, header, secret, tolerance)


class Webhooks(SyncResource, _SignatureHelpers):
    """Event destinations: an HTTPS webhook, an Amazon SNS topic or an Amazon
    SQS queue, or a messaging connection."""

    def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> SyncPage[WebhookEndpoint]:
        return self._client.get_page("/v1/webhooks", {"limit": limit, "cursor": cursor})

    def create(
        self,
        *,
        url: Optional[str] = None,
        type: Optional[str] = None,
        topic_arn: Optional[str] = None,
        queue_url: Optional[str] = None,
        aws: Optional[Mapping[str, Any]] = None,
        connection_id: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> WebhookEndpoint:
        """Create a destination with exactly one target:

        - ``url``: an HTTPS endpoint
        - ``topic_arn`` and ``aws``: an SNS topic
        - ``queue_url`` and ``aws``: an SQS queue
        - ``connection_id``: an ``sqs``, ``sns`` or ``webhook`` connection

        ``aws`` is ``{"access_key_id", "secret_access_key", "region"?,
        "endpoint"?, "message_group_id"?}``. The returned ``secret`` is shown
        only on create and rotate."""
        body = _create_body(url, type, topic_arn, queue_url, aws, connection_id, events, description)
        return cast(WebhookEndpoint, self._client.request("POST", "/v1/webhooks", json=body))

    def retrieve(self, id: str) -> WebhookEndpoint:
        return cast(WebhookEndpoint, self._client.request("GET", f"/v1/webhooks/{seg(id)}"))

    def update(
        self,
        id: str,
        *,
        url: Optional[str] = None,
        topic_arn: Optional[str] = None,
        queue_url: Optional[str] = None,
        aws: Optional[Mapping[str, Any]] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> WebhookEndpoint:
        """The type cannot change. In ``aws`` an omitted ``secret_access_key``
        keeps the stored one."""
        body = _update_body(url, topic_arn, queue_url, aws, events, description, enabled)
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

    def check(
        self,
        *,
        url: Optional[str] = None,
        type: Optional[str] = None,
        topic_arn: Optional[str] = None,
        queue_url: Optional[str] = None,
        aws: Optional[Mapping[str, Any]] = None,
        connection_id: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> WebhookCheck:
        """Verify a destination without saving it: check the credentials and
        send a ``webhook.test`` signed with a throwaway secret."""
        body = _create_body(url, type, topic_arn, queue_url, aws, connection_id, events, description)
        return cast(WebhookCheck, self._client.request("POST", "/v1/webhooks/check", json=body))

    def check_saved(self, id: str) -> WebhookCheck:
        """Verify a saved endpoint; the report includes the ``endpoint``."""
        return cast(WebhookCheck, self._client.request("POST", f"/v1/webhooks/{seg(id)}/check"))

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
        self,
        *,
        url: Optional[str] = None,
        type: Optional[str] = None,
        topic_arn: Optional[str] = None,
        queue_url: Optional[str] = None,
        aws: Optional[Mapping[str, Any]] = None,
        connection_id: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> WebhookEndpoint:
        body = _create_body(url, type, topic_arn, queue_url, aws, connection_id, events, description)
        return cast(WebhookEndpoint, await self._client.request("POST", "/v1/webhooks", json=body))

    async def retrieve(self, id: str) -> WebhookEndpoint:
        return cast(WebhookEndpoint, await self._client.request("GET", f"/v1/webhooks/{seg(id)}"))

    async def update(
        self,
        id: str,
        *,
        url: Optional[str] = None,
        topic_arn: Optional[str] = None,
        queue_url: Optional[str] = None,
        aws: Optional[Mapping[str, Any]] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> WebhookEndpoint:
        body = _update_body(url, topic_arn, queue_url, aws, events, description, enabled)
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

    async def check(
        self,
        *,
        url: Optional[str] = None,
        type: Optional[str] = None,
        topic_arn: Optional[str] = None,
        queue_url: Optional[str] = None,
        aws: Optional[Mapping[str, Any]] = None,
        connection_id: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> WebhookCheck:
        body = _create_body(url, type, topic_arn, queue_url, aws, connection_id, events, description)
        return cast(
            WebhookCheck, await self._client.request("POST", "/v1/webhooks/check", json=body)
        )

    async def check_saved(self, id: str) -> WebhookCheck:
        return cast(
            WebhookCheck, await self._client.request("POST", f"/v1/webhooks/{seg(id)}/check")
        )

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
