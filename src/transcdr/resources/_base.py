from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Mapping, Union

if TYPE_CHECKING:
    from .._base_client import AsyncAPIClient, SyncAPIClient


class SyncResource:
    def __init__(self, client: "SyncAPIClient") -> None:
        self._client = client


class AsyncResource:
    def __init__(self, client: "AsyncAPIClient") -> None:
        self._client = client


def coerce_input(value: Union[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """Accept a job input as a dict, a URL string, or an ``ast_`` asset id."""
    if isinstance(value, str):
        if value.startswith("ast_"):
            return {"type": "asset", "asset_id": value}
        return {"type": "url", "url": value}
    return dict(value)
