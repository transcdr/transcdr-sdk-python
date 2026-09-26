from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, Mapping, Optional, Union, cast

from .._base_client import new_idempotency_key, strip_none
from .._base_client import path_segment as seg
from .._errors import WaitTimeoutError
from ..pagination import AsyncPage, SyncPage
from ..types import (
    TERMINAL_JOB_STATUSES,
    Delivery,
    Destination,
    Job,
    JobEvent,
    JobOutput,
    OutputSpec,
    SignedUrl,
)
from ._base import AsyncResource, SyncResource, coerce_input

__all__ = ["Jobs", "AsyncJobs", "Deliveries", "AsyncDeliveries"]

JobInputArg = Union[str, Mapping[str, Any]]


def _create_body(
    input: JobInputArg,
    preset: Optional[str],
    output: Optional[OutputSpec],
    priority: Optional[str],
    metadata: Optional[Dict[str, str]],
    webhook_url: Optional[str],
    destination: Optional[Destination],
) -> Dict[str, Any]:
    return strip_none(
        {
            "input": coerce_input(input),
            "preset": preset,
            "output": output,
            "priority": priority,
            "metadata": metadata,
            "webhook_url": webhook_url,
            "destination": destination,
        }
    )


def _list_params(
    status: Optional[str],
    preset: Optional[str],
    created_after: Any,
    created_before: Any,
    metadata: Optional[Dict[str, str]],
    limit: Optional[int],
    cursor: Optional[str],
) -> Dict[str, Any]:
    return {
        "status": status,
        "preset": preset,
        "created_after": created_after,
        "created_before": created_before,
        "metadata": metadata,
        "limit": limit,
        "cursor": cursor,
    }


def _file_path(path: str) -> str:
    return "/".join(seg(part) for part in path.split("/"))


def _timeout_message(id: str, status: Any, timeout: Optional[float]) -> str:
    return f"Job {id} was still {status} after {timeout} s."


class Jobs(SyncResource):
    def create(
        self,
        *,
        input: JobInputArg,
        preset: Optional[str] = None,
        output: Optional[OutputSpec] = None,
        priority: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        webhook_url: Optional[str] = None,
        destination: Optional[Destination] = None,
        idempotency_key: Optional[str] = None,
    ) -> Job:
        """Queue a transcode.

        ``input`` is ``{"type": "url", "url": ...}``, ``{"type": "asset",
        "asset_id": ...}``, ``{"type": "connection", "connection_id": ...,
        "path": ...}``, or simply a URL string or ``ast_`` id. ``output``
        fields override the preset's. ``destination={"connection_id": ...,
        "prefix": "out/{job_id}/"}`` delivers every output file on completion. An ``Idempotency-Key`` is generated when
        not given, so retries never create duplicate jobs.
        """
        body = _create_body(input, preset, output, priority, metadata, webhook_url, destination)
        return cast(
            Job,
            self._client.request(
                "POST", "/v1/jobs", json=body, idempotency_key=idempotency_key or new_idempotency_key()
            ),
        )

    def list(
        self,
        *,
        status: Optional[str] = None,
        preset: Optional[str] = None,
        created_after: Any = None,
        created_before: Any = None,
        metadata: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> SyncPage[Job]:
        """Newest first. ``metadata={"customer": "42"}`` filters on ``metadata[customer]=42``."""
        params = _list_params(status, preset, created_after, created_before, metadata, limit, cursor)
        return self._client.get_page("/v1/jobs", params)

    def retrieve(self, id: str) -> Job:
        return cast(Job, self._client.request("GET", f"/v1/jobs/{seg(id)}"))

    def cancel(self, id: str) -> Job:
        return cast(Job, self._client.request("POST", f"/v1/jobs/{seg(id)}/cancel"))

    def retry(self, id: str) -> Job:
        """Start a new attempt of a failed or canceled job (same id)."""
        return cast(Job, self._client.request("POST", f"/v1/jobs/{seg(id)}/retry"))

    def delete(self, id: str) -> None:
        """Delete a terminal job and its outputs."""
        self._client.request("DELETE", f"/v1/jobs/{seg(id)}")

    def events(self, id: str) -> SyncPage[JobEvent]:
        """The job's timeline."""
        return self._client.get_page(f"/v1/jobs/{seg(id)}/events")

    def outputs(self, id: str) -> SyncPage[JobOutput]:
        return self._client.get_page(f"/v1/jobs/{seg(id)}/outputs")

    def output_url(self, id: str, label: str) -> SignedUrl:
        """A short-lived signed download URL for one output (``{url, expires_at}``)."""
        return cast(
            SignedUrl,
            self._client.request(
                "GET", f"/v1/jobs/{seg(id)}/outputs/{seg(label)}", params={"redirect": False}
            ),
        )

    def file_url(self, id: str, path: str) -> SignedUrl:
        """A short-lived signed URL for a file in an HLS package, e.g. ``master.m3u8``."""
        return cast(
            SignedUrl,
            self._client.request(
                "GET", f"/v1/jobs/{seg(id)}/files/{_file_path(path)}", params={"redirect": False}
            ),
        )

    def deliveries(self, id: str) -> SyncPage[Delivery]:
        """Deliveries of this job's outputs to connections."""
        return self._client.get_page(f"/v1/jobs/{seg(id)}/deliveries")

    def deliver(self, id: str, *, connection_id: str, prefix: Optional[str] = None) -> Delivery:
        """Deliver (again) every output file to a connection."""
        body = strip_none({"connection_id": connection_id, "prefix": prefix})
        return cast(
            Delivery, self._client.request("POST", f"/v1/jobs/{seg(id)}/deliveries", json=body)
        )

    def wait(
        self,
        id: str,
        *,
        poll_interval: float = 2.0,
        timeout: Optional[float] = None,
        on_progress: Optional[Callable[[Job], None]] = None,
    ) -> Job:
        """Poll until the job is ``completed``, ``failed`` or ``canceled`` and return it.

        ``on_progress(job)`` is called after every poll. Raises
        :class:`~transcdr.WaitTimeoutError` if ``timeout`` seconds pass first.
        Check ``job["status"]`` on return — a failed job is returned, not raised.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            job = self.retrieve(id)
            if on_progress is not None:
                on_progress(job)
            if job.get("status") in TERMINAL_JOB_STATUSES:
                return job
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WaitTimeoutError(
                        _timeout_message(id, job.get("status"), timeout), job=job
                    )
                time.sleep(min(poll_interval, remaining))
            else:
                time.sleep(poll_interval)


class AsyncJobs(AsyncResource):
    async def create(
        self,
        *,
        input: JobInputArg,
        preset: Optional[str] = None,
        output: Optional[OutputSpec] = None,
        priority: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        webhook_url: Optional[str] = None,
        destination: Optional[Destination] = None,
        idempotency_key: Optional[str] = None,
    ) -> Job:
        body = _create_body(input, preset, output, priority, metadata, webhook_url, destination)
        return cast(
            Job,
            await self._client.request(
                "POST", "/v1/jobs", json=body, idempotency_key=idempotency_key or new_idempotency_key()
            ),
        )

    async def list(
        self,
        *,
        status: Optional[str] = None,
        preset: Optional[str] = None,
        created_after: Any = None,
        created_before: Any = None,
        metadata: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> AsyncPage[Job]:
        params = _list_params(status, preset, created_after, created_before, metadata, limit, cursor)
        return await self._client.get_page("/v1/jobs", params)

    async def retrieve(self, id: str) -> Job:
        return cast(Job, await self._client.request("GET", f"/v1/jobs/{seg(id)}"))

    async def cancel(self, id: str) -> Job:
        return cast(Job, await self._client.request("POST", f"/v1/jobs/{seg(id)}/cancel"))

    async def retry(self, id: str) -> Job:
        return cast(Job, await self._client.request("POST", f"/v1/jobs/{seg(id)}/retry"))

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/jobs/{seg(id)}")

    async def events(self, id: str) -> AsyncPage[JobEvent]:
        return await self._client.get_page(f"/v1/jobs/{seg(id)}/events")

    async def outputs(self, id: str) -> AsyncPage[JobOutput]:
        return await self._client.get_page(f"/v1/jobs/{seg(id)}/outputs")

    async def output_url(self, id: str, label: str) -> SignedUrl:
        return cast(
            SignedUrl,
            await self._client.request(
                "GET", f"/v1/jobs/{seg(id)}/outputs/{seg(label)}", params={"redirect": False}
            ),
        )

    async def file_url(self, id: str, path: str) -> SignedUrl:
        return cast(
            SignedUrl,
            await self._client.request(
                "GET", f"/v1/jobs/{seg(id)}/files/{_file_path(path)}", params={"redirect": False}
            ),
        )

    async def deliveries(self, id: str) -> AsyncPage[Delivery]:
        return await self._client.get_page(f"/v1/jobs/{seg(id)}/deliveries")

    async def deliver(
        self, id: str, *, connection_id: str, prefix: Optional[str] = None
    ) -> Delivery:
        body = strip_none({"connection_id": connection_id, "prefix": prefix})
        return cast(
            Delivery,
            await self._client.request("POST", f"/v1/jobs/{seg(id)}/deliveries", json=body),
        )

    async def wait(
        self,
        id: str,
        *,
        poll_interval: float = 2.0,
        timeout: Optional[float] = None,
        on_progress: Optional[Callable[[Job], Any]] = None,
    ) -> Job:
        """Async twin of :meth:`Jobs.wait`. ``on_progress`` may be sync or async."""
        loop = asyncio.get_running_loop()
        deadline = None if timeout is None else loop.time() + timeout
        while True:
            job = await self.retrieve(id)
            if on_progress is not None:
                result = on_progress(job)
                if asyncio.iscoroutine(result):
                    await result
            if job.get("status") in TERMINAL_JOB_STATUSES:
                return job
            if deadline is not None:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise WaitTimeoutError(
                        _timeout_message(id, job.get("status"), timeout), job=job
                    )
                await asyncio.sleep(min(poll_interval, remaining))
            else:
                await asyncio.sleep(poll_interval)


class Deliveries(SyncResource):
    """Deliveries of job outputs to connections (see ``jobs.deliveries``)."""

    def retry(self, id: str) -> Delivery:
        """Retry a failed delivery now."""
        return cast(Delivery, self._client.request("POST", f"/v1/deliveries/{seg(id)}/retry"))


class AsyncDeliveries(AsyncResource):
    async def retry(self, id: str) -> Delivery:
        return cast(
            Delivery, await self._client.request("POST", f"/v1/deliveries/{seg(id)}/retry")
        )
