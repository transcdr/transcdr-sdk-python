from __future__ import annotations

from typing import Any, Dict, Optional, cast

from .._base_client import path_segment as seg
from .._base_client import strip_none
from ..pagination import AsyncPage, SyncPage
from ..types import Connection, ConnectionTestResult, RemoteObject
from ._base import AsyncResource, SyncResource

__all__ = ["Connections", "AsyncConnections"]


def _browse_params(
    prefix: Optional[str], recursive: Optional[bool], limit: Optional[int], cursor: Optional[str]
) -> Dict[str, Any]:
    return {"prefix": prefix, "recursive": recursive, "limit": limit, "cursor": cursor}


class Connections(SyncResource):
    """Your storage (S3/R2/B2/MinIO, GCS, Azure Blob, FTP(S), SFTP, HTTP, WebDAV):
    where job inputs come from and outputs are delivered to."""

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
        """Create a connection. It is tested before it is saved; a failing
        check raises :class:`~transcdr.InvalidRequestError`. Secrets are write-only."""
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
    ) -> Connection:
        """``config`` merges into the existing one. An omitted secret is kept;
        ``""`` clears it."""
        body = strip_none({"name": name, "config": config, "secrets": secrets})
        return cast(
            Connection, self._client.request("PATCH", f"/v1/connections/{seg(id)}", json=body)
        )

    def delete(self, id: str) -> None:
        """Raises a 409 :class:`~transcdr.InvalidRequestError` while an automation uses it."""
        self._client.request("DELETE", f"/v1/connections/{seg(id)}")

    def test(self, id: str) -> ConnectionTestResult:
        """Re-check the connection: ``{ok, error, connection}``."""
        return cast(
            ConnectionTestResult,
            self._client.request("POST", f"/v1/connections/{seg(id)}/test"),
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
    ) -> Connection:
        body = strip_none({"name": name, "config": config, "secrets": secrets})
        return cast(
            Connection,
            await self._client.request("PATCH", f"/v1/connections/{seg(id)}", json=body),
        )

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/connections/{seg(id)}")

    async def test(self, id: str) -> ConnectionTestResult:
        return cast(
            ConnectionTestResult,
            await self._client.request("POST", f"/v1/connections/{seg(id)}/test"),
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
