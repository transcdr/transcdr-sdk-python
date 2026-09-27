from __future__ import annotations

from typing import Optional, cast

from .._base_client import path_segment as seg
from .._base_client import NOT_GIVEN, strip_none, strip_not_given
from ..pagination import AsyncPage, SyncPage
from .._errors import TranscdrError
from ..types import AuthResponse, Me, Membership, Organization, User, is_session
from ._base import AsyncResource, SyncResource

__all__ = [
    "OrganizationResource",
    "Members",
    "Organizations",
    "AsyncOrganizationResource",
    "AsyncMembers",
    "AsyncOrganizations",
]


class Members(SyncResource):
    def list(self, *, limit: Optional[int] = None, cursor: Optional[str] = None) -> SyncPage[User]:
        return self._client.get_page(
            "/v1/organization/members", {"limit": limit, "cursor": cursor}
        )

    def create(
        self,
        *,
        email: str,
        role: str,
        name: Optional[str] = None,
        password: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> User:
        """Add a member (owner/admin only). ``role``: ``owner`` | ``admin`` | ``member``.

        The email of an existing Transcdr user gives that user access (``name``
        and ``password`` are refused); an unknown email creates the user, and
        then ``name`` and ``password`` are required."""
        body = strip_none({"email": email, "role": role, "name": name, "password": password})
        return cast(User, self._client._create("/v1/organization/members", body, idempotency_key))

    def update(self, id: str, *, role: str) -> User:
        return cast(
            User,
            self._client.request("PATCH", f"/v1/organization/members/{seg(id)}", json={"role": role}),
        )

    def delete(self, id: str) -> None:
        self._client.request("DELETE", f"/v1/organization/members/{seg(id)}")

    def leave(self) -> None:
        """Leave the organization: remove the signed-in user's own membership
        (session tokens only). The last owner cannot leave (409 ``last_owner``)."""
        me = cast(Me, self._client.request("GET", "/v1/me"))
        self.delete(_own_user_id(me))


def _own_user_id(me: Me) -> str:
    user = me.get("user")
    # An API key has no membership of its own to leave, even though the API
    # reports the user who created it. (A session has an api_key too: tds_.)
    if not user or not is_session(me):
        raise TranscdrError("members.leave() needs a session token, not an API key.")
    return user["id"]


class Organizations(SyncResource):
    """The organizations the signed-in user belongs to (session tokens only)."""

    def list(self) -> SyncPage[Membership]:
        return self._client.get_page("/v1/organizations")

    def create(self, *, name: str, idempotency_key: Optional[str] = None) -> AuthResponse:
        """Create an organization owned by the caller. Returns a session token
        in it; the current token keeps working."""
        return cast(AuthResponse, self._client._create("/v1/organizations", {"name": name}, idempotency_key))


class OrganizationResource(SyncResource):
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        super().__init__(client)
        self.members = Members(client)

    def retrieve(self) -> Organization:
        return cast(Organization, self._client.request("GET", "/v1/organization"))

    def update(
        self, *, name: Optional[str] = None, billing_email: Optional[str] = NOT_GIVEN
    ) -> Organization:
        """``billing_email=None`` (or ``""``) clears it."""
        body = {**strip_none({"name": name}), **strip_not_given({"billing_email": billing_email})}
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

    async def create(
        self,
        *,
        email: str,
        role: str,
        name: Optional[str] = None,
        password: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> User:
        body = strip_none({"email": email, "role": role, "name": name, "password": password})
        return cast(User, await self._client._create("/v1/organization/members", body, idempotency_key))

    async def update(self, id: str, *, role: str) -> User:
        return cast(
            User,
            await self._client.request(
                "PATCH", f"/v1/organization/members/{seg(id)}", json={"role": role}
            ),
        )

    async def delete(self, id: str) -> None:
        await self._client.request("DELETE", f"/v1/organization/members/{seg(id)}")

    async def leave(self) -> None:
        me = cast(Me, await self._client.request("GET", "/v1/me"))
        await self.delete(_own_user_id(me))


class AsyncOrganizations(AsyncResource):
    async def list(self) -> AsyncPage[Membership]:
        return await self._client.get_page("/v1/organizations")

    async def create(self, *, name: str, idempotency_key: Optional[str] = None) -> AuthResponse:
        return cast(
            AuthResponse, await self._client._create("/v1/organizations", {"name": name}, idempotency_key)
        )


class AsyncOrganizationResource(AsyncResource):
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        super().__init__(client)
        self.members = AsyncMembers(client)

    async def retrieve(self) -> Organization:
        return cast(Organization, await self._client.request("GET", "/v1/organization"))

    async def update(
        self, *, name: Optional[str] = None, billing_email: Optional[str] = NOT_GIVEN
    ) -> Organization:
        body = {**strip_none({"name": name}), **strip_not_given({"billing_email": billing_email})}
        return cast(Organization, await self._client.request("PATCH", "/v1/organization", json=body))

    async def rotate_job_webhook_secret(self) -> Organization:
        return cast(
            Organization,
            await self._client.request("POST", "/v1/organization/rotate-job-webhook-secret"),
        )
