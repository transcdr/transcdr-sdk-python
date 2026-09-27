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


# --------------------------------------------------------------------------
# The vector shared with the TypeScript and Go SDKs' tests
# --------------------------------------------------------------------------

TS_SECRET = "whsec_test_secret"
TS_TIMESTAMP = 1_700_000_000
TS_BODY = '{"id":"evt_1","type":"job.completed"}'
TS_EXPECTED = "76323e66a6eb95011512d61a834db013378975ecf841d3d43eb14fcb08fbb0e4"
TS_HEADER = f"t={TS_TIMESTAMP},v1={TS_EXPECTED}"


def test_shared_vector():
    assert compute_signature(TS_BODY, TS_SECRET, TS_TIMESTAMP) == TS_EXPECTED
    assert sign_payload(TS_BODY, TS_SECRET, TS_TIMESTAMP) == TS_HEADER
    assert verify_signature(TS_BODY, TS_HEADER, TS_SECRET, now=TS_TIMESTAMP + 300)
    assert not verify_signature(TS_BODY, TS_HEADER, TS_SECRET, now=TS_TIMESTAMP + 301)


# --------------------------------------------------------------------------
# Amazon SNS / SQS destinations
# --------------------------------------------------------------------------

from transcdr.webhooks import (  # noqa: E402
    SIGNATURE_ATTRIBUTE,
    signature_from_attributes,
    verify_sns_sqs_signature,
)


@pytest.mark.parametrize(
    "attributes",
    [
        # SQS ReceiveMessage / boto3
        {"transcdr-signature": {"DataType": "String", "StringValue": TS_HEADER}},
        # Lambda SQS event
        {"transcdr-signature": {"dataType": "String", "stringValue": TS_HEADER}},
        # SNS notification JSON
        {"transcdr-signature": {"Type": "String", "Value": TS_HEADER}},
        # A plain string map, and a key in another case
        {"Transcdr-Signature": TS_HEADER},
        # The attribute value itself
        TS_HEADER,
    ],
)
def test_sns_sqs_attribute_shapes(attributes):
    assert signature_from_attributes(attributes) == TS_HEADER
    assert verify_sns_sqs_signature(TS_BODY, attributes, TS_SECRET, now=TS_TIMESTAMP)
    assert not verify_sns_sqs_signature(TS_BODY + " ", attributes, TS_SECRET, now=TS_TIMESTAMP)
    assert not verify_sns_sqs_signature(TS_BODY, attributes, "whsec_other", now=TS_TIMESTAMP)


@pytest.mark.parametrize("attributes", [None, {}, {"other": {"StringValue": TS_HEADER}}, {"transcdr-signature": {}}, 42])
def test_sns_sqs_missing_signature(attributes):
    assert signature_from_attributes(attributes) is None
    assert not verify_sns_sqs_signature(TS_BODY, attributes, TS_SECRET, now=TS_TIMESTAMP)


def test_sns_sqs_attribute_name_and_client_helper():
    assert SIGNATURE_ATTRIBUTE == "transcdr-signature"
    client = Transcdr(api_key="tdk_test_example")
    attrs = {"transcdr-signature": {"StringValue": sign_payload(TS_BODY, TS_SECRET)}}
    assert client.webhooks.verify_sns_sqs_signature(TS_BODY, attrs, TS_SECRET)
    client.close()
