from __future__ import annotations

from typing import Optional, cast

from .._base_client import path_segment as seg
from .._base_client import strip_none
from ..pagination import AsyncPage, SyncPage
from ..types import Organization, User
from ._base import AsyncResource, SyncResource

__all__ = ["OrganizationResource", "Members", "AsyncOrganizationResource", "AsyncMembers"]


class Members(SyncResource):
    def list(self, *, limit: Optional[int] = None, cursor: Optional[str] = None) -> SyncPage[User]:
        return self._client.get_page(
            "/v1/organization/members", {"limit": limit, "cursor": cursor}
        )

    def create(self, *, name: str, email: str, role: str, password: str) -> User:
        """Add a member (owner/admin only). ``role``: ``owner`` | ``admin`` | ``member``."""
        body = {"name": name, "email": email, "role": role, "password": password}
        return cast(User, self._client.request("POST", "/v1/organization/members", json=body))

    def update(self, id: str, *, role: str) -> User:
        return cast(
            User,
            self._client.request("PATCH", f"/v1/organization/members/{seg(id)}", json={"role": role}),
        )

    def delete(self, id: str) -> None:
        self._client.request("DELETE", f"/v1/organization/members/{seg(id)}")


class OrganizationResource(SyncResource):
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        super().__init__(client)
        self.members = Members(client)

    def retrieve(self) -> Organization:
        return cast(Organization, self._client.request("GET", "/v1/organization"))

    def update(self, *, name: Optional[str] = None, billing_email: Optional[str] = None) -> Organization:
        body = strip_none({"name": name, "billing_email": billing_email})
        return cast(Organization, self._client.request("PATCH", "/v1/organization", json=body))

    def rotate_job_webhook_secret(self) -> Organization:
        """New secret for per-job ``webhook_url`` deliveries (``job_webhook_secret``)."""
        return cast(
            Organization,
            self._client.request("POST", "/v1/organization/rotate-job-webhook-secret"),
        )


class AsyncMembers(AsyncResource):
    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> AsyncPage[User]:
        return await self._client.get_page(
            "/v1/organization/members", {"limit": limit, "cursor": cursor}
        )

    async def create(self, *, name: str, email: str, role: str, password: str) -> User:
        body = {"name": name, "email": email, "role": role, "password": password}
        return cast(User, await self._client.request("POST", "/v1/organization/members", json=body))

    async def update(self, id: str, *, role: str) -> User:
        return cast(
            User,
            await self._client.request(
                "PATCH", f"/v1/organization/members/{seg(id)}", json={"role": role}
            ),
        )

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/organization/members/{seg(id)}")


class AsyncOrganizationResource(AsyncResource):
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        super().__init__(client)
        self.members = AsyncMembers(client)

    async def retrieve(self) -> Organization:
        return cast(Organization, await self._client.request("GET", "/v1/organization"))

    async def update(
        self, *, name: Optional[str] = None, billing_email: Optional[str] = None
    ) -> Organization:
        body = strip_none({"name": name, "billing_email": billing_email})
        return cast(Organization, await self._client.request("PATCH", "/v1/organization", json=body))

    async def rotate_job_webhook_secret(self) -> Organization:
        return cast(
            Organization,
            await self._client.request("POST", "/v1/organization/rotate-job-webhook-secret"),
        )
