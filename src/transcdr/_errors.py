"""Exceptions raised by the Transcdr SDK.

Every API error has the shape documented in the API contract::

    {"error": {"type", "code", "message", "param", "details", "request_id"}}

and is mapped onto a :class:`TranscdrError` subclass by HTTP status.
"""

from __future__ import annotations

import email.utils
import time
from typing import Any, Dict, Mapping, Optional

__all__ = [
    "TranscdrError",
    "APIConnectionError",
    "APITimeoutError",
    "AuthenticationError",
    "PermissionDeniedError",
    "InvalidRequestError",
    "NotFoundError",
    "RateLimitError",
    "QuotaError",
    "APIError",
    "SignatureVerificationError",
    "WaitTimeoutError",
]


class TranscdrError(Exception):
    """Base class for every error raised by the SDK."""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        type: Optional[str] = None,
        code: Optional[str] = None,
        param: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.type = type
        self.code = code
        self.param = param
        self.details = details
        self.request_id = request_id
        self.headers: Dict[str, str] = dict(headers or {})
        self.body = body

    def __str__(self) -> str:
        parts = []
        if self.status is not None:
            parts.append(str(self.status))
        if self.code:
            parts.append(self.code)
        prefix = f"[{' '.join(parts)}] " if parts else ""
        suffix = f" (request_id={self.request_id})" if self.request_id else ""
        return f"{prefix}{self.message}{suffix}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, status={self.status!r}, "
            f"type={self.type!r}, code={self.code!r}, request_id={self.request_id!r})"
        )


class APIConnectionError(TranscdrError):
    """The API could not be reached (DNS, TLS, connection reset, …)."""


class APITimeoutError(APIConnectionError):
    """The request timed out."""


class AuthenticationError(TranscdrError):
    """401 — missing, invalid, expired or revoked credentials."""


class PermissionDeniedError(TranscdrError):
    """403 — the key lacks a scope (``insufficient_scope``) or the role is too low."""


class InvalidRequestError(TranscdrError):
    """400/404/409/422 — the request was malformed or failed validation."""


class NotFoundError(InvalidRequestError):
    """404 — the object does not exist (or belongs to another organization)."""


class RateLimitError(TranscdrError):
    """429 — too many requests. ``retry_after`` is in seconds when the API sent it."""

    @property
    def retry_after(self) -> Optional[float]:
        return parse_retry_after(self.headers)


class QuotaError(TranscdrError):
    """402 — not enough credit (``insufficient_credit``), the job would cost
    more than its ``max_cost_cents`` (``cost_limit_exceeded``), or the monthly
    spending limit is reached (``spend_limit_reached``)."""


class APIError(TranscdrError):
    """5xx, or any other unexpected response from the API."""


class SignatureVerificationError(TranscdrError):
    """A webhook payload's ``Transcdr-Signature`` did not verify."""

    def __init__(self, message: str, *, header: Optional[str] = None, payload: Any = None) -> None:
        super().__init__(message, type="signature_verification_error")
        self.sig_header = header
        self.payload = payload


class WaitTimeoutError(TranscdrError):
    """``jobs.wait`` gave up before the job reached a terminal status."""

    def __init__(self, message: str, *, job: Any = None) -> None:
        super().__init__(message, type="wait_timeout")
        self.job = job


_BY_TYPE = {
    "authentication_error": AuthenticationError,
    "permission_error": PermissionDeniedError,
    "invalid_request_error": InvalidRequestError,
    "rate_limit_error": RateLimitError,
    "quota_error": QuotaError,
    "api_error": APIError,
}


def _class_for(status: int, error_type: Optional[str]) -> type:
    if status == 401:
        return AuthenticationError
    if status == 403:
        return PermissionDeniedError
    if status == 402:
        return QuotaError
    if status == 404:
        return NotFoundError
    if status == 429:
        return RateLimitError
    if status >= 500:
        return APIError
    if error_type in _BY_TYPE:
        return _BY_TYPE[error_type]
    if 400 <= status < 500:
        return InvalidRequestError
    return APIError


def error_from_response(status: int, body: Any, headers: Mapping[str, str]) -> TranscdrError:
    """Build the right exception for a non-2xx response."""
    err: Dict[str, Any] = {}
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        err = body["error"]
    message = err.get("message")
    if not message:
        if isinstance(body, str) and body.strip():
            message = body.strip()[:500]
        else:
            message = f"HTTP {status}"
    request_id = err.get("request_id") or headers.get("x-request-id")
    cls = _class_for(status, err.get("type"))
    return cls(
        message,
        status=status,
        type=err.get("type"),
        code=err.get("code"),
        param=err.get("param"),
        details=err.get("details"),
        request_id=request_id,
        headers=headers,
        body=body,
    )


def parse_retry_after(headers: Mapping[str, str]) -> Optional[float]:
    """Seconds from a ``Retry-After`` header (delta-seconds or HTTP date)."""
    value = None
    for key, val in headers.items():
        if key.lower() == "retry-after":
            value = val
            break
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    return max(0.0, parsed.timestamp() - time.time())
