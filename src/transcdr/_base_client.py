"""HTTP plumbing shared by :class:`~transcdr.Transcdr` and :class:`~transcdr.AsyncTranscdr`."""

from __future__ import annotations

import asyncio
import datetime as _dt
import os
import platform
import random
import time
import uuid
from typing import Any, Dict, List, Mapping, Optional, Tuple, TypeVar, Union
from urllib.parse import quote

import httpx

from ._errors import (
    APIConnectionError,
    APITimeoutError,
    error_from_response,
    parse_retry_after,
)
from ._version import __version__
from .pagination import AsyncPage, SyncPage

DEFAULT_BASE_URL = "https://api.transcdr.com"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2
INITIAL_RETRY_DELAY = 0.5
MAX_RETRY_DELAY = 8.0
#: A ``Retry-After`` longer than this is not honoured by automatic retries.
MAX_RETRY_AFTER = 60.0

# Safe to replay without an Idempotency-Key.
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "DELETE", "PUT"})

T = TypeVar("T")
Params = Optional[Mapping[str, Any]]
Timeout = Union[float, httpx.Timeout, None]


class _NotGiven:
    """Distinguishes "leave unchanged" from ``None`` (which is sent as JSON
    ``null`` and clears a value where the API allows it)."""

    def __repr__(self) -> str:
        return "NOT_GIVEN"

    def __bool__(self) -> bool:
        return False


NOT_GIVEN: Any = _NotGiven()


def strip_not_given(values: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop keys left as :data:`NOT_GIVEN`; keep ``None`` (sent as ``null``)."""
    return {k: v for k, v in values.items() if v is not NOT_GIVEN}


def new_idempotency_key() -> str:
    return str(uuid.uuid4())


def strip_none(values: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop keys whose value is ``None`` (the SDK's "not given")."""
    return {k: v for k, v in values.items() if v is not None}


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    return str(value)


def encode_query(params: Params) -> List[Tuple[str, str]]:
    """Flatten query params: ``None`` is dropped, bools become ``true``/``false``,
    dicts become ``key[sub]=value`` (e.g. ``metadata[customer]=42``) and lists
    repeat the key."""
    out: List[Tuple[str, str]] = []
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, Mapping):
            for sub, sub_value in value.items():
                if sub_value is not None:
                    out.append((f"{key}[{sub}]", _scalar(sub_value)))
        elif isinstance(value, (list, tuple, set, frozenset)):
            out.extend((key, _scalar(v)) for v in value)
        else:
            out.append((key, _scalar(value)))
    return out


def path_segment(value: str) -> str:
    """Percent-encode one path segment (ids, labels, slugs)."""
    return quote(str(value), safe="")


class BaseClient:
    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: Timeout,
        max_retries: int,
        default_headers: Optional[Mapping[str, str]],
    ) -> None:
        if api_key is None:
            api_key = os.environ.get("TRANSCDR_API_KEY")
        if base_url is None:
            base_url = os.environ.get("TRANSCDR_BASE_URL") or DEFAULT_BASE_URL
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self.api_key: Optional[str] = api_key
        self.base_url: str = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers: Dict[str, str] = dict(default_headers or {})

    @property
    def livemode(self) -> Optional[bool]:
        """``False`` for ``tdk_test_`` keys, ``True`` for ``tdk_live_`` keys,
        ``None`` for session tokens or no key."""
        if not self.api_key:
            return None
        if self.api_key.startswith("tdk_test_"):
            return False
        if self.api_key.startswith("tdk_live_"):
            return True
        return None

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    def _headers(
        self, extra: Optional[Mapping[str, str]], idempotency_key: Optional[str]
    ) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": f"transcdr-python/{__version__}",
            "X-Transcdr-Client": (
                f"python/{__version__}; {platform.python_implementation()} {platform.python_version()}"
            ),
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.default_headers)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _retryable_method(method: str, headers: Mapping[str, str]) -> bool:
        if method in _IDEMPOTENT_METHODS:
            return True
        return any(k.lower() == "idempotency-key" for k in headers)

    @staticmethod
    def _retryable_status(status: int) -> bool:
        return status in (408, 429) or status >= 500

    @staticmethod
    def _retry_delay(attempt: int, response: Optional[httpx.Response] = None) -> float:
        """Exponential backoff with jitter; honours a short ``Retry-After``."""
        if response is not None:
            retry_after = parse_retry_after(response.headers)
            if retry_after is not None and retry_after <= MAX_RETRY_AFTER:
                return retry_after
        delay = min(INITIAL_RETRY_DELAY * (2**attempt), MAX_RETRY_DELAY)
        return delay * (1 - 0.25 * random.random())

    @staticmethod
    def _parse_body(response: httpx.Response) -> Any:
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    def _handle(self, response: httpx.Response) -> Any:
        status = response.status_code
        if 300 <= status < 400 and "location" in response.headers:
            # Download routes answer with a 302 to a signed URL; hand the URL back.
            return {"url": response.headers["location"]}
        body = self._parse_body(response)
        if 200 <= status < 300:
            return body
        raise error_from_response(status, body, response.headers)

    @staticmethod
    def _connection_error(exc: Exception) -> APIConnectionError:
        if isinstance(exc, httpx.TimeoutException):
            return APITimeoutError(f"Request timed out: {exc}")
        return APIConnectionError(f"Could not reach the Transcdr API: {exc}")


class SyncAPIClient(BaseClient):
    _client: httpx.Client

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout, follow_redirects=False)

    # Tests replace this to avoid real sleeps.
    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Params = None,
        json: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        idempotency_key: Optional[str] = None,
        timeout: Timeout = None,
        max_retries: Optional[int] = None,
    ) -> Any:
        """Call any endpoint and return the decoded JSON body.

        An escape hatch for routes the SDK does not wrap yet, and what every
        resource method uses underneath."""
        method = method.upper()
        url = self._url(path)
        request_headers = self._headers(headers, idempotency_key)
        retries = self.max_retries if max_retries is None else max_retries
        can_retry = self._retryable_method(method, request_headers)
        query = encode_query(params)
        attempt = 0
        while True:
            try:
                response = self._client.request(
                    method,
                    url,
                    params=query or None,
                    json=json,
                    headers=request_headers,
                    timeout=timeout if timeout is not None else self.timeout,
                )
            except httpx.TransportError as exc:
                if can_retry and attempt < retries:
                    self._sleep(self._retry_delay(attempt))
                    attempt += 1
                    continue
                raise self._connection_error(exc) from exc
            if can_retry and attempt < retries and self._retryable_status(response.status_code):
                response.close()
                self._sleep(self._retry_delay(attempt, response))
                attempt += 1
                continue
            return self._handle(response)

    def get_page(self, path: str, params: Params = None) -> SyncPage[Any]:
        base = dict(params or {})

        def fetch(cursor: str) -> SyncPage[Any]:
            return self.get_page(path, {**base, "cursor": cursor})

        return SyncPage(self.request("GET", path, params=base), fetch)

    def close(self) -> None:
        """Close the underlying HTTP connection pool (if the client created it)."""
        if self._owns_client:
            self._client.close()

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class AsyncAPIClient(BaseClient):
    _client: httpx.AsyncClient

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout, follow_redirects=False)

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Params = None,
        json: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        idempotency_key: Optional[str] = None,
        timeout: Timeout = None,
        max_retries: Optional[int] = None,
    ) -> Any:
        """Call any endpoint and return the decoded JSON body."""
        method = method.upper()
        url = self._url(path)
        request_headers = self._headers(headers, idempotency_key)
        retries = self.max_retries if max_retries is None else max_retries
        can_retry = self._retryable_method(method, request_headers)
        query = encode_query(params)
        attempt = 0
        while True:
            try:
                response = await self._client.request(
                    method,
                    url,
                    params=query or None,
                    json=json,
                    headers=request_headers,
                    timeout=timeout if timeout is not None else self.timeout,
                )
            except httpx.TransportError as exc:
                if can_retry and attempt < retries:
                    await self._sleep(self._retry_delay(attempt))
                    attempt += 1
                    continue
                raise self._connection_error(exc) from exc
            if can_retry and attempt < retries and self._retryable_status(response.status_code):
                await response.aclose()
                await self._sleep(self._retry_delay(attempt, response))
                attempt += 1
                continue
            return self._handle(response)

    async def get_page(self, path: str, params: Params = None) -> AsyncPage[Any]:
        base = dict(params or {})

        async def fetch(cursor: str) -> AsyncPage[Any]:
            return await self.get_page(path, {**base, "cursor": cursor})

        return AsyncPage(await self.request("GET", path, params=base), fetch)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self: T) -> T:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
