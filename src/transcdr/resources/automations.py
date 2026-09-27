from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, cast

from .._base_client import path_segment as seg
from .._base_client import strip_none
from ..pagination import AsyncPage, SyncPage
from ..types import (
    Automation,
    AutomationItem,
    AutomationRunResult,
    AutomationTriggerResult,
    AutomationSource,
    Destination,
    OutputSpec,
)
from ._base import AsyncResource, SyncResource

__all__ = ["Automations", "AsyncAutomations"]


def _body(
    name: Optional[str],
    source: Optional[AutomationSource],
    trigger: Optional[str],
    preset: Optional[str],
    output: Optional[OutputSpec],
    destination: Optional[Destination],
    poll_interval_seconds: Optional[int],
    settle_seconds: Optional[int],
    after_success: Optional[str],
    priority: Optional[str],
    metadata: Optional[Dict[str, str]],
    webhook_url: Optional[str],
    enabled: Optional[bool],
    trigger_connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    return strip_none(
        {
            "name": name,
            "enabled": enabled,
            "trigger": trigger,
            "trigger_connection_id": trigger_connection_id,
            "source": source,
            "poll_interval_seconds": poll_interval_seconds,
            "settle_seconds": settle_seconds,
            "preset": preset,
            "output": output,
            "destination": destination,
            "after_success": after_success,
            "priority": priority,
            "metadata": metadata,
            "webhook_url": webhook_url,
        }
    )


def _trigger_body(path: Optional[str], paths: Optional[List[str]]) -> Mapping[str, Any]:
    if (path is None) == (paths is None):
        raise TypeError("pass exactly one of path= or paths=")
    return {"path": path} if path is not None else {"paths": list(paths or [])}


class Automations(SyncResource):
    """When a file lands in a connection, transcode it and deliver the outputs.

    ``trigger="watch"`` polls the source every ``poll_interval_seconds`` and
    takes files unchanged for ``settle_seconds``; ``trigger="hook"`` takes
    pushes at the automation's ``hook_url``; ``trigger="queue"`` consumes the
    ``sqs`` connection ``trigger_connection_id`` (S3 notifications, directly
    or through SNS, EventBridge events and job requests). Each object version
    is processed exactly once.

    To clear a value on ``update``: ``preset=""``, ``webhook_url=""``,
    ``trigger_connection_id=""``, ``output={}``, ``metadata={}``."""

    def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> SyncPage[Automation]:
        return self._client.get_page("/v1/automations", {"limit": limit, "cursor": cursor})

    def create(
        self,
        *,
        name: str,
        source: AutomationSource,
        trigger: Optional[str] = None,
        preset: Optional[str] = None,
        output: Optional[OutputSpec] = None,
        destination: Optional[Destination] = None,
        poll_interval_seconds: Optional[int] = None,
        settle_seconds: Optional[int] = None,
        after_success: Optional[str] = None,
        priority: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        webhook_url: Optional[str] = None,
        enabled: Optional[bool] = None,
        trigger_connection_id: Optional[str] = None,
    ) -> Automation:
        body = _body(
            name, source, trigger, preset, output, destination, poll_interval_seconds,
            settle_seconds, after_success, priority, metadata, webhook_url, enabled,
            trigger_connection_id,
        )  # fmt: skip
        return cast(Automation, self._client.request("POST", "/v1/automations", json=body))

    def retrieve(self, id: str) -> Automation:
        return cast(Automation, self._client.request("GET", f"/v1/automations/{seg(id)}"))

    def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        source: Optional[AutomationSource] = None,
        trigger: Optional[str] = None,
        preset: Optional[str] = None,
        output: Optional[OutputSpec] = None,
        destination: Optional[Destination] = None,
        poll_interval_seconds: Optional[int] = None,
        settle_seconds: Optional[int] = None,
        after_success: Optional[str] = None,
        priority: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        webhook_url: Optional[str] = None,
        enabled: Optional[bool] = None,
        trigger_connection_id: Optional[str] = None,
    ) -> Automation:
        body = _body(
            name, source, trigger, preset, output, destination, poll_interval_seconds,
            settle_seconds, after_success, priority, metadata, webhook_url, enabled,
            trigger_connection_id,
        )  # fmt: skip
        return cast(
            Automation, self._client.request("PATCH", f"/v1/automations/{seg(id)}", json=body)
        )

    def delete(self, id: str) -> None:
        self._client.request("DELETE", f"/v1/automations/{seg(id)}")

    def run(self, id: str) -> AutomationRunResult:
        """Poll the source now (``{jobs_created}``), or for a queue automation read
        one batch from the queue (``{messages_received, messages_deleted, jobs_created}``)."""
        return cast(
            AutomationRunResult, self._client.request("POST", f"/v1/automations/{seg(id)}/run")
        )

    def trigger(
        self, id: str, *, path: Optional[str] = None, paths: Optional[List[str]] = None
    ) -> AutomationTriggerResult:
        """Process specific files now: ``{jobs_created, job_ids}``."""
        return cast(
            AutomationTriggerResult,
            self._client.request(
                "POST", f"/v1/automations/{seg(id)}/trigger", json=_trigger_body(path, paths)
            ),
        )

    def rotate_hook_token(self, id: str) -> Automation:
        """Issue a new ``hook_url``; the old one stops working."""
        return cast(
            Automation,
            self._client.request("POST", f"/v1/automations/{seg(id)}/rotate-hook-token"),
        )

    def items(
        self, id: str, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> SyncPage[AutomationItem]:
        """Objects the automation has processed: ``{path, size_bytes, status, job_id, error}``."""
        return self._client.get_page(
            f"/v1/automations/{seg(id)}/items", {"limit": limit, "cursor": cursor}
        )


class AsyncAutomations(AsyncResource):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[Automation]:
        return await self._client.get_page("/v1/automations", {"limit": limit, "cursor": cursor})

    async def create(
        self,
        *,
        name: str,
        source: AutomationSource,
        trigger: Optional[str] = None,
        preset: Optional[str] = None,
        output: Optional[OutputSpec] = None,
        destination: Optional[Destination] = None,
        poll_interval_seconds: Optional[int] = None,
        settle_seconds: Optional[int] = None,
        after_success: Optional[str] = None,
        priority: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        webhook_url: Optional[str] = None,
        enabled: Optional[bool] = None,
        trigger_connection_id: Optional[str] = None,
    ) -> Automation:
        body = _body(
            name, source, trigger, preset, output, destination, poll_interval_seconds,
            settle_seconds, after_success, priority, metadata, webhook_url, enabled,
            trigger_connection_id,
        )  # fmt: skip
        return cast(Automation, await self._client.request("POST", "/v1/automations", json=body))

    async def retrieve(self, id: str) -> Automation:
        return cast(Automation, await self._client.request("GET", f"/v1/automations/{seg(id)}"))

    async def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        source: Optional[AutomationSource] = None,
        trigger: Optional[str] = None,
        preset: Optional[str] = None,
        output: Optional[OutputSpec] = None,
        destination: Optional[Destination] = None,
        poll_interval_seconds: Optional[int] = None,
        settle_seconds: Optional[int] = None,
        after_success: Optional[str] = None,
        priority: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        webhook_url: Optional[str] = None,
        enabled: Optional[bool] = None,
        trigger_connection_id: Optional[str] = None,
    ) -> Automation:
        body = _body(
            name, source, trigger, preset, output, destination, poll_interval_seconds,
            settle_seconds, after_success, priority, metadata, webhook_url, enabled,
            trigger_connection_id,
        )  # fmt: skip
        return cast(
            Automation,
            await self._client.request("PATCH", f"/v1/automations/{seg(id)}", json=body),
        )

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/automations/{seg(id)}")

    async def run(self, id: str) -> AutomationRunResult:
        return cast(
            AutomationRunResult,
            await self._client.request("POST", f"/v1/automations/{seg(id)}/run"),
        )

    async def trigger(
        self, id: str, *, path: Optional[str] = None, paths: Optional[List[str]] = None
    ) -> AutomationTriggerResult:
        return cast(
            AutomationTriggerResult,
            await self._client.request(
                "POST", f"/v1/automations/{seg(id)}/trigger", json=_trigger_body(path, paths)
            ),
        )

    async def rotate_hook_token(self, id: str) -> Automation:
        return cast(
            Automation,
            await self._client.request("POST", f"/v1/automations/{seg(id)}/rotate-hook-token"),
        )

    async def items(
        self, id: str, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[AutomationItem]:
        return await self._client.get_page(
            f"/v1/automations/{seg(id)}/items", {"limit": limit, "cursor": cursor}
        )
