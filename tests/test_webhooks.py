from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from transcdr import SignatureVerificationError, Transcdr
from transcdr.webhooks import (
    SIGNATURE_HEADER,
    compute_signature,
    construct_event,
    parse_signature_header,
    sign_payload,
    verify_signature,
)

SECRET = "whsec_test_4f1b2c3d4e5f60718293a4b5c6d7e8f9"
NOW = 1_790_000_000
BODY = json.dumps(
    {
        "object": "event",
        "id": "evt_0123456789abcdefghijkl",
        "type": "job.completed",
        "created_at": "2026-09-26T12:00:00Z",
        "data": {"object": {"object": "job", "id": "job_1", "status": "completed"}},
    },
    separators=(",", ":"),
).encode()


def reference_signature(secret: str, timestamp: int, body: bytes) -> str:
    """Independent implementation of the documented scheme."""
    return hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


def header_for(timestamp: int = NOW, body: bytes = BODY, secret: str = SECRET) -> str:
    return f"t={timestamp},v1={reference_signature(secret, timestamp, body)}"


def test_header_name():
    assert SIGNATURE_HEADER == "Transcdr-Signature"


def test_compute_signature_matches_reference_vector():
    assert compute_signature(BODY, SECRET, NOW) == reference_signature(SECRET, NOW, BODY)
    assert sign_payload(BODY, SECRET, NOW) == header_for()


def test_verify_valid_bytes_and_str():
    assert verify_signature(BODY, header_for(), SECRET, now=NOW)
    assert verify_signature(BODY.decode(), header_for(), SECRET, now=NOW)
    assert verify_signature(bytearray(BODY), header_for(), SECRET, now=NOW)


def test_verify_within_tolerance():
    assert verify_signature(BODY, header_for(NOW - 299), SECRET, now=NOW)
    assert verify_signature(BODY, header_for(NOW + 299), SECRET, now=NOW)


def test_verify_rejects_stale_and_future_timestamps():
    assert not verify_signature(BODY, header_for(NOW - 301), SECRET, now=NOW)
    assert not verify_signature(BODY, header_for(NOW + 301), SECRET, now=NOW)
    assert verify_signature(BODY, header_for(NOW - 1000), SECRET, tolerance=3600, now=NOW)


def test_verify_rejects_tampering():
    assert not verify_signature(BODY + b" ", header_for(), SECRET, now=NOW)
    assert not verify_signature(BODY, header_for(), SECRET + "x", now=NOW)
    # Changing the signed timestamp invalidates the signature.
    sig = reference_signature(SECRET, NOW, BODY)
    assert not verify_signature(BODY, f"t={NOW + 1},v1={sig}", SECRET, now=NOW)


def test_verify_rejects_malformed_headers():
    for header in [None, "", "garbage", f"t={NOW}", "v1=abc", f"t=abc,v1={'0' * 64}"]:
        assert not verify_signature(BODY, header, SECRET, now=NOW)
    assert not verify_signature(BODY, header_for(), "", now=NOW)


def test_multiple_signatures_and_whitespace():
    good = reference_signature(SECRET, NOW, BODY)
    header = f"t={NOW}, v1={'0' * 64}, v1={good.upper()}, v0=legacy"
    assert parse_signature_header(header) == (NOW, ["0" * 64, good])
    assert verify_signature(BODY, header, SECRET, now=NOW)


def test_construct_event():
    event = construct_event(BODY, header_for(), SECRET, now=NOW)
    assert event["type"] == "job.completed"
    assert event["data"]["object"]["id"] == "job_1"


def test_construct_event_raises_on_bad_signature():
    with pytest.raises(SignatureVerificationError) as info:
        construct_event(BODY, header_for(NOW - 3600), SECRET, now=NOW)
    assert "tolerance" in info.value.message
    assert info.value.sig_header == header_for(NOW - 3600)

    with pytest.raises(SignatureVerificationError):
        construct_event(BODY, "t=1,v1=deadbeef", SECRET, now=1)


def test_construct_event_raises_on_non_json():
    body = b"not json"
    with pytest.raises(SignatureVerificationError):
        construct_event(body, header_for(body=body), SECRET, now=NOW)


def test_default_uses_current_time():
    header = sign_payload(BODY, SECRET)
    assert verify_signature(BODY, header, SECRET)


def test_client_helpers_delegate():
    client = Transcdr(api_key="tdk_test_x")
    header = sign_payload(BODY, SECRET)
    assert client.webhooks.verify_signature(BODY, header, SECRET)
    assert client.webhooks.construct_event(BODY, header, SECRET)["id"].startswith("evt_")
    client.close()
