"""Idempotent creates, preset replace, clearing with ``None``, API key lookup,
secret fingerprints and telling a session from an API key."""

from __future__ import annotations

import json

import httpx
import pytest

from transcdr import InvalidRequestError, NotFoundError, is_session

from .conftest import SINGLE_MP4, AsyncRecorder, Recorder, error_body, json_response

PRESET = {"object": "preset", "id": "pre_1", "slug": "mine", "name": "Mine", "version": 1, "output": SINGLE_MP4}
FP = {"set": True, "fingerprint": "hmac-sha256:3f9a0c1b2d4e"}

CREATES = [
    ("/v1/assets", lambda c: c.assets.create(url="https://example.com/a.mp4")),
    ("/v1/presets", lambda c: c.presets.create(name="Mine", output=SINGLE_MP4)),
    ("/v1/webhooks", lambda c: c.webhooks.create(url="https://example.com/hook")),
    ("/v1/connections", lambda c: c.connections.create(name="c", kind="s3", config={"bucket": "b"})),
    ("/v1/automations", lambda c: c.automations.create(name="a", source={"connection_id": "con_1"}, preset="hls-av1-abr")),
    ("/v1/api-keys", lambda c: c.api_keys.create(name="CI")),
    ("/v1/organization/members", lambda c: c.organization.members.create(email="a@b.c", role="member")),
    ("/v1/organizations", lambda c: c.organizations.create(name="Acme")),
    ("/v1/probe", lambda c: c.probe.create(input="https://example.com/a.mp4")),
]


@pytest.mark.parametrize("path,call", CREATES, ids=[p for p, _ in CREATES])
def test_every_create_sends_an_idempotency_key(make_client, path, call):
    rec = Recorder(json_response(201, {"id": "x_1"}))
    call(make_client(rec))
    req = rec.requests[0]
    assert (req.method, req.url.path) == ("POST", path)
    assert len(req.headers["Idempotency-Key"]) >= 16


def test_create_takes_an_explicit_key(make_client):
    rec = Recorder(json_response(201, PRESET))
    make_client(rec).presets.create(name="Mine", output=SINGLE_MP4, idempotency_key="preset-mine")
    assert rec.requests[0].headers["Idempotency-Key"] == "preset-mine"


def test_create_is_retried_with_the_same_key(make_client, sleeps):
    rec = Recorder(
        json_response(503, error_body("api_error", "unavailable", "down")),
        httpx.ConnectError("reset"),
        json_response(201, PRESET, {"Idempotent-Replayed": "true"}),
    )
    preset = make_client(rec).presets.create(name="Mine", output=SINGLE_MP4)
    assert preset["id"] == "pre_1"
    assert len(rec.requests) == 3
    assert len({r.headers["Idempotency-Key"] for r in rec.requests}) == 1


def test_key_reused_is_not_retried(make_client, sleeps):
    rec = Recorder(json_response(409, error_body("invalid_request_error", "idempotency_key_reused", "x")))
    with pytest.raises(InvalidRequestError) as exc:
        make_client(rec).webhooks.create(url="https://example.com/hook", idempotency_key="k1")
    assert exc.value.code == "idempotency_key_reused"
    assert len(rec.requests) == 1 and sleeps == []


def test_non_create_posts_carry_no_key(make_client):
    rec = Recorder(json_response(200, {"id": "whk_1"}))
    make_client(rec).webhooks.rotate_secret("whk_1")
    assert "Idempotency-Key" not in rec.requests[0].headers


def test_preset_replace_is_put(make_client):
    rec = Recorder(json_response(200, PRESET))
    make_client(rec).presets.replace("pre_1", name="Mine", output=SINGLE_MP4)
    req = rec.requests[0]
    assert (req.method, req.url.path) == ("PUT", "/v1/presets/pre_1")
    assert rec.json() == {"name": "Mine", "output": SINGLE_MP4}
    assert "Idempotency-Key" not in req.headers


def test_preset_update_clears_with_none(make_client):
    rec = Recorder(json_response(200, PRESET), json_response(200, PRESET))
    client = make_client(rec)
    client.presets.update("pre_1", description=None, metadata=None)
    assert rec.json(0) == {"description": None, "metadata": None}
    client.presets.update("pre_1", name="Renamed")
    assert rec.json(1) == {"name": "Renamed"}


def test_automation_update_clears_with_none_and_keeps_what_is_left_out(make_client):
    rec = Recorder(json_response(200, {}), json_response(200, {}), json_response(201, {}))
    client = make_client(rec)
    client.automations.update(
        "aut_1",
        destination=None,
        preset=None,
        output=None,
        metadata=None,
        webhook_url=None,
        trigger_connection_id=None,
    )
    assert rec.json(0) == {
        "destination": None,
        "preset": None,
        "output": None,
        "metadata": None,
        "webhook_url": None,
        "trigger_connection_id": None,
    }
    client.automations.update("aut_1", name="x", enabled=None)
    assert rec.json(1) == {"name": "x"}
    # On create, None still means "not given".
    client.automations.create(name="a", source={"connection_id": "con_1"}, preset=None, output=SINGLE_MP4,
                              destination=None)  # fmt: skip
    assert rec.json(2) == {"name": "a", "source": {"connection_id": "con_1"}, "output": SINGLE_MP4}


def test_webhook_connection_and_organization_clear_with_none(make_client):
    rec = Recorder(json_response(200, {}), json_response(200, {}), json_response(200, {}))
    client = make_client(rec)
    client.webhooks.update("whk_1", description=None, aws={"endpoint": None, "message_group_id": None})
    assert rec.json(0) == {"description": None, "aws": {"endpoint": None, "message_group_id": None}}
    client.connections.update("con_1", config={"endpoint": None}, secrets={"session_token": None})
    assert rec.json(1) == {"config": {"endpoint": None}, "secrets": {"session_token": None}}
    client.organization.update(billing_email=None)
    assert rec.json(2) == {"billing_email": None}


def test_api_keys_retrieve(make_client):
    rec = Recorder(
        json_response(200, {"object": "api_key", "id": "key_1", "revoked_at": None}),
        json_response(404, error_body("invalid_request_error", "not_found", "no")),
    )
    client = make_client(rec)
    key = client.api_keys.retrieve("key_1")
    assert key["revoked_at"] is None
    assert (rec.requests[0].method, rec.requests[0].url.path) == ("GET", "/v1/api-keys/key_1")
    with pytest.raises(NotFoundError):
        client.api_keys.retrieve("key_1")


def test_secret_fingerprints(make_client):
    rec = Recorder(
        json_response(200, {"object": "connection", "id": "con_1", "secrets": {"access_key_id": FP}}),
        json_response(200, {"object": "webhook_endpoint", "id": "whk_1", "secrets": {"secret": FP}}),
    )
    client = make_client(rec)
    conn = client.connections.retrieve("con_1")
    hook = client.webhooks.retrieve("whk_1")
    assert conn["secrets"]["access_key_id"]["fingerprint"].startswith("hmac-sha256:")
    assert hook["secrets"]["secret"]["set"] is True


def test_is_session():
    assert is_session({"api_key": {"prefix": "tds_ab12"}, "organizations": []})
    assert not is_session({"api_key": {"prefix": "tdk_live_ab12"}, "user": {"id": "usr_1"}})
    assert not is_session({"api_key": {"prefix": "tdk_test_ab12"}, "organizations": []})
    # Older servers: no api_key for a session, which lists its memberships.
    assert is_session({"organizations": [{"object": "membership"}]})
    assert not is_session({"api_key": None, "organizations": []})


@pytest.mark.asyncio
async def test_async_creates_and_replace(make_async_client):
    rec = AsyncRecorder(json_response(201, PRESET), json_response(200, PRESET), json_response(200, {}))
    client = make_async_client(rec)
    await client.presets.create(name="Mine", output=SINGLE_MP4)
    await client.presets.replace("pre_1", name="Mine", output=SINGLE_MP4)
    await client.automations.update("aut_1", destination=None)
    assert "Idempotency-Key" in rec.requests[0].headers
    assert rec.requests[1].method == "PUT"
    assert json.loads(rec.bodies[2]) == {"destination": None}
