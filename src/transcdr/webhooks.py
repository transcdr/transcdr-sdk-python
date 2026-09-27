"""Webhook signature verification.

Every delivery carries::

    Transcdr-Signature: t=<unix seconds>,v1=<hex hmac_sha256(secret, "<t>.<raw body>")>

Verify against the **raw** request body, before any JSON parsing::

    from transcdr.webhooks import construct_event

    event = construct_event(request.body, request.headers["Transcdr-Signature"], secret)

Amazon SNS and SQS destinations carry the same signature in the
``transcdr-signature`` message attribute, over ``"<t>.<message>"``::

    from transcdr.webhooks import verify_sns_sqs_signature

    ok = verify_sns_sqs_signature(record["body"], record["messageAttributes"], secret)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, List, Mapping, Optional, Tuple, Union, cast

from ._errors import SignatureVerificationError
from .types import Event

__all__ = [
    "SIGNATURE_HEADER",
    "DEFAULT_TOLERANCE",
    "compute_signature",
    "sign_payload",
    "parse_signature_header",
    "verify_signature",
    "construct_event",
    "SIGNATURE_ATTRIBUTE",
    "signature_from_attributes",
    "verify_sns_sqs_signature",
]

SIGNATURE_HEADER = "Transcdr-Signature"
#: The message attribute carrying the signature on SNS and SQS deliveries.
SIGNATURE_ATTRIBUTE = "transcdr-signature"
DEFAULT_TOLERANCE = 300

Payload = Union[bytes, bytearray, memoryview, str]


def _to_bytes(payload: Payload) -> bytes:
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return bytes(payload)


def compute_signature(payload: Payload, secret: str, timestamp: int) -> str:
    """Lowercase hex HMAC-SHA256 of ``"<timestamp>.<payload>"`` under ``secret``."""
    message = str(int(timestamp)).encode("ascii") + b"." + _to_bytes(payload)
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def sign_payload(payload: Payload, secret: str, timestamp: Optional[int] = None) -> str:
    """Build a ``Transcdr-Signature`` header value — handy for testing your receiver."""
    ts = int(time.time()) if timestamp is None else int(timestamp)
    return f"t={ts},v1={compute_signature(payload, secret, ts)}"


def parse_signature_header(header: str) -> Tuple[Optional[int], List[str]]:
    """Parse ``t=…,v1=…[,v1=…]`` into ``(timestamp, [signatures])``."""
    timestamp: Optional[int] = None
    signatures: List[str] = []
    for part in header.split(","):
        key, sep, value = part.partition("=")
        if not sep:
            continue
        key, value = key.strip(), value.strip()
        if key == "t" and value.isdigit():
            timestamp = int(value)
        elif key == "v1" and value:
            signatures.append(value.lower())
    return timestamp, signatures


def _check(
    payload: Payload,
    header: Optional[str],
    secret: str,
    tolerance: Optional[int],
    now: Optional[float],
) -> Optional[str]:
    """``None`` when valid, else the reason it is not."""
    if not header:
        return "Missing Transcdr-Signature header."
    if not secret:
        return "No webhook secret configured."
    timestamp, signatures = parse_signature_header(header)
    if timestamp is None:
        return "Transcdr-Signature header has no timestamp."
    if not signatures:
        return "Transcdr-Signature header has no v1 signature."
    current = time.time() if now is None else now
    if tolerance is not None and tolerance > 0 and abs(current - timestamp) > tolerance:
        return "Timestamp outside the tolerance zone."
    expected = compute_signature(payload, secret, timestamp)
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        return "No signature matches the expected signature for the payload."
    return None


def verify_signature(
    payload: Payload,
    header: Optional[str],
    secret: str,
    tolerance: Optional[int] = DEFAULT_TOLERANCE,
    *,
    now: Optional[float] = None,
) -> bool:
    """Whether ``header`` is a valid signature of the raw ``payload``.

    ``tolerance`` is the allowed clock skew in seconds (``None``/``0`` disables
    the check — not recommended, it re-opens replay attacks). ``now`` overrides
    the current unix time, for tests.
    """
    return _check(payload, header, secret, tolerance, now) is None


def construct_event(
    payload: Payload,
    header: Optional[str],
    secret: str,
    tolerance: Optional[int] = DEFAULT_TOLERANCE,
    *,
    now: Optional[float] = None,
) -> Event:
    """Verify the signature, then parse the body into an :class:`~transcdr.types.Event`.

    Raises :class:`~transcdr.SignatureVerificationError` when the signature is
    missing, stale or wrong, or the body is not a JSON object."""
    reason = _check(payload, header, secret, tolerance, now)
    if reason is not None:
        raise SignatureVerificationError(reason, header=header, payload=payload)
    try:
        event = json.loads(_to_bytes(payload).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise SignatureVerificationError(
            f"Webhook payload is not valid JSON: {exc}", header=header, payload=payload
        ) from exc
    if not isinstance(event, dict):
        raise SignatureVerificationError(
            "Webhook payload is not a JSON object.", header=header, payload=payload
        )
    return cast(Event, event)


# --------------------------------------------------------------------------
# Amazon SNS / SQS destinations
# --------------------------------------------------------------------------


def _attribute_value(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("StringValue", "stringValue", "Value"):
            found = value.get(key)
            if isinstance(found, str):
                return found
    return None


def signature_from_attributes(attributes: Any) -> Optional[str]:
    """Read the ``transcdr-signature`` value out of an SNS or SQS
    message-attribute map in any AWS shape: SQS ``ReceiveMessage`` and boto3
    (``StringValue``), Lambda SQS events (``stringValue``), SNS notification
    JSON (``Value``), a plain string value, or the attribute value itself."""
    if attributes is None:
        return None
    if isinstance(attributes, str):
        return attributes
    if not isinstance(attributes, Mapping):
        return None
    for key, value in attributes.items():
        if isinstance(key, str) and key.lower() == SIGNATURE_ATTRIBUTE:
            return _attribute_value(value)
    return None


def verify_sns_sqs_signature(
    message: Payload,
    attributes: Any,
    secret: str,
    tolerance: Optional[int] = DEFAULT_TOLERANCE,
    *,
    now: Optional[float] = None,
) -> bool:
    """Verify an Amazon SNS or SQS delivery: the ``transcdr-signature``
    attribute is ``t=<unix>,v1=<hmac>`` over ``"<t>.<message>"``.

    ``message`` is the SNS ``Message`` or the SQS body (Lambda:
    ``record["body"]``) exactly as received; ``attributes`` is the
    message-attribute map in any AWS shape, or the attribute value itself.
    With raw message delivery off, an SNS to SQS subscription wraps the
    notification: parse the body and pass its ``Message`` and
    ``MessageAttributes`` instead."""
    return verify_signature(message, signature_from_attributes(attributes), secret, tolerance, now=now)
