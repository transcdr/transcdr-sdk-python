from __future__ import annotations

from typing import Optional, cast

from .._base_client import strip_none

from ..types import AuthResponse, Me
from ._base import AsyncResource, SyncResource

__all__ = ["Auth", "AsyncAuth"]


class Auth(SyncResource):
    """Session auth for dashboard-style apps. Most integrations use an API key instead.

    Returned tokens are not applied automatically: ``client.api_key = resp["token"]``.
    """

    def register(
        self, *, name: str, email: str, password: str, organization_name: str
    ) -> AuthResponse:
        body = {
            "name": name,
            "email": email,
            "password": password,
            "organization_name": organization_name,
        }
        return cast(AuthResponse, self._client.request("POST", "/v1/auth/register", json=body))

    def login(
        self, *, email: str, password: str, organization_id: Optional[str] = None
    ) -> AuthResponse:
        """Exchange an email and password for a session token. ``organization_id``
        picks the organization; by default the one used last."""
        body = strip_none({"email": email, "password": password, "organization_id": organization_id})
        return cast(AuthResponse, self._client.request("POST", "/v1/auth/login", json=body))

    def switch(self, organization_id: str) -> AuthResponse:
        """Issue a session token for another of the user's organizations
        (session tokens only). The current token is revoked: set the new one
        with ``client.api_key = resp["token"]``."""
        return cast(
            AuthResponse,
            self._client.request("POST", "/v1/auth/switch", json={"organization_id": organization_id}),
        )

    def logout(self) -> None:
        """Revoke the session token in use."""
        self._client.request("POST", "/v1/auth/logout")

    def change_password(self, *, current_password: str, new_password: str) -> None:
        """Change the password; other sessions are revoked."""
        body = {"current_password": current_password, "new_password": new_password}
        self._client.request("POST", "/v1/auth/password", json=body)

    def me(self) -> Me:
        """The user (for session tokens), organization, the user's organizations
        and the scopes behind the credential."""
        return cast(Me, self._client.request("GET", "/v1/me"))


class AsyncAuth(AsyncResource):
    async def register(
        self, *, name: str, email: str, password: str, organization_name: str
    ) -> AuthResponse:
        body = {
            "name": name,
            "email": email,
            "password": password,
            "organization_name": organization_name,
        }
        return cast(AuthResponse, await self._client.request("POST", "/v1/auth/register", json=body))

    async def login(
        self, *, email: str, password: str, organization_id: Optional[str] = None
    ) -> AuthResponse:
        body = strip_none({"email": email, "password": password, "organization_id": organization_id})
        return cast(AuthResponse, await self._client.request("POST", "/v1/auth/login", json=body))

    async def switch(self, organization_id: str) -> AuthResponse:
        return cast(
            AuthResponse,
            await self._client.request(
                "POST", "/v1/auth/switch", json={"organization_id": organization_id}
            ),
        )

    async def logout(self) -> None:
        await self._client.request("POST", "/v1/auth/logout")

    async def change_password(self, *, current_password: str, new_password: str) -> None:
        body = {"current_password": current_password, "new_password": new_password}
        await self._client.request("POST", "/v1/auth/password", json=body)

    async def me(self) -> Me:
        return cast(Me, await self._client.request("GET", "/v1/me"))
