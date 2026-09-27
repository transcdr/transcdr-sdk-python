from __future__ import annotations

from typing import Any, Dict, Optional, cast

from .._base_client import path_segment as seg
from .._base_client import strip_none
from ..pagination import AsyncPage, SyncPage
from ..types import Connection, ConnectionCheck, ConnectionTestResult, RemoteObject
from ._base import AsyncResource, SyncResource

__all__ = ["Connections", "AsyncConnections"]


def _browse_params(
    prefix: Optional[str], recursive: Optional[bool], limit: Optional[int], cursor: Optional[str]
) -> Dict[str, Any]:
    return {"prefix": prefix, "recursive": recursive, "limit": limit, "cursor": cursor}


def _update_body(
    name: Optional[str],
    config: Optional[Dict[str, Any]],
    secrets: Optional[Dict[str, str]],
    enabled: Optional[bool],
) -> Dict[str, Any]:
    return strip_none({"name": name, "enabled": enabled, "config": config, "secrets": secrets})


class Connections(SyncResource):
    """Your storage (S3/R2/B2/MinIO, GCS, Azure Blob, FTP(S), SFTP, HTTP, WebDAV):
    where job inputs come from and outputs are delivered to; and messaging
    connections (``sqs``, ``sns``, ``webhook``), which receive events. An
    ``sqs`` connection can also trigger queue automations."""

    def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> SyncPage[Connection]:
        return self._client.get_page("/v1/connections", {"limit": limit, "cursor": cursor})

    def create(
        self,
        *,
        name: str,
        kind: str,
        config: Dict[str, Any],
        secrets: Optional[Dict[str, str]] = None,
    ) -> Connection:
        """Create a connection. It is tested when it is saved: the outcome is
        in ``status`` and ``last_error``. Secrets are write-only."""
        body = strip_none({"name": name, "kind": kind, "config": config, "secrets": secrets})
        return cast(Connection, self._client.request("POST", "/v1/connections", json=body))

    def retrieve(self, id: str) -> Connection:
        return cast(Connection, self._client.request("GET", f"/v1/connections/{seg(id)}"))

    def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, str]] = None,
        enabled: Optional[bool] = None,
    ) -> Connection:
        """``config`` merges into the existing one (a ``None`` value clears that
        field). An omitted secret is kept; ``""`` clears it. ``enabled=True``
        turns a disabled connection back on (the failure count resets and it
        is tested again); ``enabled=False`` turns it off."""
        body = _update_body(name, config, secrets, enabled)
        return cast(
            Connection, self._client.request("PATCH", f"/v1/connections/{seg(id)}", json=body)
        )

    def enable(self, id: str) -> Connection:
        """Turn a connection back on after it was disabled; it is tested again."""
        return self.update(id, enabled=True)

    def disable(self, id: str) -> Connection:
        """Turn a connection off by hand. Anything using it is refused with 409
        ``connection_disabled`` until it is back on."""
        return self.update(id, enabled=False)

    def delete(self, id: str) -> None:
        """Raises a 409 :class:`~transcdr.InvalidRequestError` while an automation uses it."""
        self._client.request("DELETE", f"/v1/connections/{seg(id)}")

    def test(self, id: str) -> ConnectionTestResult:
        """Re-check the connection: ``{ok, error, connection}``."""
        return cast(
            ConnectionTestResult,
            self._client.request("POST", f"/v1/connections/{seg(id)}/test"),
        )

    def check(
        self,
        *,
        kind: str,
        config: Dict[str, Any],
        secrets: Optional[Dict[str, str]] = None,
        name: Optional[str] = None,
    ) -> ConnectionCheck:
        """Verify settings without saving them: sign in, list, write a probe
        object, read it back and delete it, and report each step with the
        roles it can serve and provider-specific setup (e.g. an IAM policy)."""
        body = strip_none({"name": name, "kind": kind, "config": config, "secrets": secrets})
        return cast(ConnectionCheck, self._client.request("POST", "/v1/connections/check", json=body))

    def check_saved(self, id: str) -> ConnectionCheck:
        """Verify a saved connection; also updates its ``status`` and ``last_error``."""
        return cast(
            ConnectionCheck, self._client.request("POST", f"/v1/connections/{seg(id)}/check")
        )

    def browse(
        self,
        id: str,
        *,
        prefix: Optional[str] = None,
        recursive: Optional[bool] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> SyncPage[RemoteObject]:
        """List files under ``prefix`` (``{path, size, last_modified}``)."""
        return self._client.get_page(
            f"/v1/connections/{seg(id)}/browse", _browse_params(prefix, recursive, limit, cursor)
        )


class AsyncConnections(AsyncResource):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[Connection]:
        return await self._client.get_page("/v1/connections", {"limit": limit, "cursor": cursor})

    async def create(
        self,
        *,
        name: str,
        kind: str,
        config: Dict[str, Any],
        secrets: Optional[Dict[str, str]] = None,
    ) -> Connection:
        body = strip_none({"name": name, "kind": kind, "config": config, "secrets": secrets})
        return cast(Connection, await self._client.request("POST", "/v1/connections", json=body))

    async def retrieve(self, id: str) -> Connection:
        return cast(Connection, await self._client.request("GET", f"/v1/connections/{seg(id)}"))

    async def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, str]] = None,
        enabled: Optional[bool] = None,
    ) -> Connection:
        body = _update_body(name, config, secrets, enabled)
        return cast(
            Connection,
            await self._client.request("PATCH", f"/v1/connections/{seg(id)}", json=body),
        )

    async def enable(self, id: str) -> Connection:
        return await self.update(id, enabled=True)

    async def disable(self, id: str) -> Connection:
        return await self.update(id, enabled=False)

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/connections/{seg(id)}")

    async def test(self, id: str) -> ConnectionTestResult:
        return cast(
            ConnectionTestResult,
            await self._client.request("POST", f"/v1/connections/{seg(id)}/test"),
        )

    async def check(
        self,
        *,
        kind: str,
        config: Dict[str, Any],
        secrets: Optional[Dict[str, str]] = None,
        name: Optional[str] = None,
    ) -> ConnectionCheck:
        body = strip_none({"name": name, "kind": kind, "config": config, "secrets": secrets})
        return cast(
            ConnectionCheck, await self._client.request("POST", "/v1/connections/check", json=body)
        )

    async def check_saved(self, id: str) -> ConnectionCheck:
        return cast(
            ConnectionCheck,
            await self._client.request("POST", f"/v1/connections/{seg(id)}/check"),
        )

    async def browse(
        self,
        id: str,
        *,
        prefix: Optional[str] = None,
        recursive: Optional[bool] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> AsyncPage[RemoteObject]:
        return await self._client.get_page(
            f"/v1/connections/{seg(id)}/browse", _browse_params(prefix, recursive, limit, cursor)
        )
