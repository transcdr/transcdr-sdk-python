from __future__ import annotations

import pytest

from transcdr import InvalidRequestError

from .conftest import AsyncRecorder, Recorder, error_body, json_response
from .test_client import query

CONNECTION = {
    "object": "connection",
    "id": "con_1",
    "name": "Ingest bucket",
    "kind": "s3",
    "config": {"bucket": "ingest", "region": "auto"},
    "secrets_set": ["access_key_id", "secret_access_key"],
    "capabilities": {"source": True, "destination": True, "watch": True},
    "status": "ok",
}
AUTOMATION = {"object": "automation", "id": "aut_1", "name": "Ingest", "trigger": "watch", "enabled": True}
DELIVERY = {"object": "delivery", "id": "dlv_1", "connection_id": "con_1", "status": "pending"}
PATTERN = "**/*.{mp4,mov}"


def listing(*items, cursor=None):
    return json_response(
        200, {"object": "list", "data": list(items), "has_more": cursor is not None, "next_cursor": cursor}
    )


def routes(rec):
    return [(r.method, r.url.path) for r in rec.requests]


# --------------------------------------------------------------------------
# Connections
# --------------------------------------------------------------------------


def test_connection_crud(make_client):
    rec = Recorder(
        json_response(201, CONNECTION),
        json_response(200, CONNECTION),
        json_response(200, {**CONNECTION, "name": "Renamed"}),
        listing(CONNECTION),
        json_response(200, {"ok": True, "error": None, "connection": CONNECTION}),
        json_response(204, None),
    )
    client = make_client(rec)
    config = {"bucket": "ingest", "region": "auto", "endpoint": "https://acct.r2.cloudflarestorage.com"}
    created = client.connections.create(
        name="Ingest bucket",
        kind="s3",
        config=config,
        secrets={"access_key_id": "AK", "secret_access_key": "SK"},
    )
    assert created["secrets_set"] == ["access_key_id", "secret_access_key"]
    client.connections.retrieve("con_1")
    client.connections.update("con_1", name="Renamed", secrets={"session_token": ""})
    assert [c["id"] for c in client.connections.list(limit=5)] == ["con_1"]
    assert client.connections.test("con_1")["ok"] is True
    client.connections.delete("con_1")

    assert routes(rec) == [
        ("POST", "/v1/connections"),
        ("GET", "/v1/connections/con_1"),
        ("PATCH", "/v1/connections/con_1"),
        ("GET", "/v1/connections"),
        ("POST", "/v1/connections/con_1/test"),
        ("DELETE", "/v1/connections/con_1"),
    ]
    assert rec.json(0) == {
        "name": "Ingest bucket",
        "kind": "s3",
        "config": config,
        "secrets": {"access_key_id": "AK", "secret_access_key": "SK"},
    }
    # Omitted fields are not sent; "" (clear a secret) is.
    assert rec.json(2) == {"name": "Renamed", "secrets": {"session_token": ""}}
    assert query(rec.requests[3]) == [("limit", "5")]


def test_connection_browse_paginates(make_client):
    rec = Recorder(
        listing({"object": "remote_object", "path": "incoming/a.mp4", "size": 10}, cursor="c1"),
        listing({"object": "remote_object", "path": "incoming/b.mov", "size": 20}),
    )
    page = make_client(rec).connections.browse("con_1", prefix="incoming/", recursive=True)
    assert [o["path"] for o in page.auto_paging_iter()] == ["incoming/a.mp4", "incoming/b.mov"]
    assert rec.requests[0].url.path == "/v1/connections/con_1/browse"
    assert query(rec.requests[0]) == [("prefix", "incoming/"), ("recursive", "true")]
    assert query(rec.requests[1]) == [("prefix", "incoming/"), ("recursive", "true"), ("cursor", "c1")]


def test_connection_create_check_failure(make_client):
    rec = Recorder(
        json_response(
            422, error_body("invalid_request_error", "connection_failed", "Access denied", param="secrets")
        )
    )
    with pytest.raises(InvalidRequestError) as info:
        make_client(rec).connections.create(name="x", kind="sftp", config={"host": "h", "username": "u"})
    assert info.value.code == "connection_failed"
    assert len(rec.requests) == 1  # a POST without an Idempotency-Key is never retried


def test_connection_delete_in_use_conflict(make_client):
    rec = Recorder(json_response(409, error_body("invalid_request_error", "connection_in_use", "In use")))
    with pytest.raises(InvalidRequestError) as info:
        make_client(rec).connections.delete("con_1")
    assert info.value.status == 409


# --------------------------------------------------------------------------
# Automations
# --------------------------------------------------------------------------


def test_automation_crud_and_actions(make_client):
    rec = Recorder(
        json_response(201, AUTOMATION),
        json_response(200, AUTOMATION),
        json_response(200, {**AUTOMATION, "enabled": False}),
        listing(AUTOMATION),
        json_response(200, {"jobs_created": 2}),
        json_response(200, {"jobs_created": 1, "job_ids": ["job_1"]}),
        json_response(200, {"jobs_created": 2, "job_ids": ["job_2", "job_3"]}),
        json_response(200, {**AUTOMATION, "hook_url": "https://api.test/v1/hooks/automations/ahk_new"}),
        listing({"path": "incoming/a.mp4", "size_bytes": 10, "status": "completed", "job_id": "job_1", "error": None}),
        json_response(204, None),
    )
    client = make_client(rec)
    client.automations.create(
        name="Ingest",
        trigger="watch",
        source={"connection_id": "con_in", "prefix": "incoming/", "pattern": PATTERN},
        preset="hls-av1-abr",
        destination={"connection_id": "con_out", "prefix": "{automation}/{date}/{stem}/"},
        poll_interval_seconds=300,
        settle_seconds=60,
        after_success="keep",
    )
    client.automations.retrieve("aut_1")
    client.automations.update("aut_1", enabled=False)
    client.automations.list()
    assert client.automations.run("aut_1")["jobs_created"] == 2
    assert client.automations.trigger("aut_1", path="incoming/a.mp4")["job_ids"] == ["job_1"]
    client.automations.trigger("aut_1", paths=["incoming/b.mp4", "incoming/c.mp4"])
    assert client.automations.rotate_hook_token("aut_1")["hook_url"].endswith("ahk_new")
    assert client.automations.items("aut_1").data[0]["job_id"] == "job_1"
    client.automations.delete("aut_1")

    assert routes(rec) == [
        ("POST", "/v1/automations"),
        ("GET", "/v1/automations/aut_1"),
        ("PATCH", "/v1/automations/aut_1"),
        ("GET", "/v1/automations"),
        ("POST", "/v1/automations/aut_1/run"),
        ("POST", "/v1/automations/aut_1/trigger"),
        ("POST", "/v1/automations/aut_1/trigger"),
        ("POST", "/v1/automations/aut_1/rotate-hook-token"),
        ("GET", "/v1/automations/aut_1/items"),
        ("DELETE", "/v1/automations/aut_1"),
    ]
    assert rec.json(0) == {
        "name": "Ingest",
        "trigger": "watch",
        "source": {"connection_id": "con_in", "prefix": "incoming/", "pattern": PATTERN},
        "poll_interval_seconds": 300,
        "settle_seconds": 60,
        "preset": "hls-av1-abr",
        "destination": {"connection_id": "con_out", "prefix": "{automation}/{date}/{stem}/"},
        "after_success": "keep",
    }
    assert rec.json(2) == {"enabled": False}
    assert rec.json(5) == {"path": "incoming/a.mp4"}
    assert rec.json(6) == {"paths": ["incoming/b.mp4", "incoming/c.mp4"]}


@pytest.mark.parametrize("kwargs", [{}, {"path": "a", "paths": ["b"]}])
def test_automation_trigger_needs_exactly_one(make_client, kwargs):
    rec = Recorder()
    with pytest.raises(TypeError):
        make_client(rec).automations.trigger("aut_1", **kwargs)
    assert rec.requests == []


# --------------------------------------------------------------------------
# Jobs with connections, deliveries
# --------------------------------------------------------------------------


def test_job_with_connection_input_and_destination(make_client):
    rec = Recorder(json_response(201, {"object": "job", "id": "job_1", "status": "queued"}))
    make_client(rec).jobs.create(
        input={"type": "connection", "connection_id": "con_in", "path": "incoming/talk.mov"},
        preset="hls-av1-abr",
        destination={"connection_id": "con_out", "prefix": "out/{job_id}/"},
    )
    assert rec.json() == {
        "input": {"type": "connection", "connection_id": "con_in", "path": "incoming/talk.mov"},
        "preset": "hls-av1-abr",
        "destination": {"connection_id": "con_out", "prefix": "out/{job_id}/"},
    }
    assert "Idempotency-Key" in rec.requests[0].headers


def test_job_deliveries_deliver_and_retry(make_client):
    rec = Recorder(
        listing({**DELIVERY, "status": "failed"}),
        json_response(201, DELIVERY),
        json_response(201, DELIVERY),
        json_response(200, {**DELIVERY, "status": "pending", "attempts": 2}),
    )
    client = make_client(rec)
    assert client.jobs.deliveries("job_1").data[0]["status"] == "failed"
    client.jobs.deliver("job_1", connection_id="con_out", prefix="again/{job_id}/")
    client.jobs.deliver("job_1", connection_id="con_out")
    assert client.deliveries.retry("dlv_1")["attempts"] == 2
    assert routes(rec) == [
        ("GET", "/v1/jobs/job_1/deliveries"),
        ("POST", "/v1/jobs/job_1/deliveries"),
        ("POST", "/v1/jobs/job_1/deliveries"),
        ("POST", "/v1/deliveries/dlv_1/retry"),
    ]
    assert rec.json(1) == {"connection_id": "con_out", "prefix": "again/{job_id}/"}
    assert rec.json(2) == {"connection_id": "con_out"}


# --------------------------------------------------------------------------
# Async
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_integrations(make_async_client):
    rec = AsyncRecorder(
        json_response(201, CONNECTION),
        listing({"path": "a.mp4"}),
        json_response(201, AUTOMATION),
        json_response(200, {"jobs_created": 1, "job_ids": ["job_9"]}),
        listing({"path": "a.mp4", "status": "completed"}),
        json_response(201, DELIVERY),
        listing(DELIVERY),
        json_response(200, DELIVERY),
    )
    client = make_async_client(rec)
    await client.connections.create(
        name="ftp", kind="ftps", config={"host": "ftp.example.com", "username": "u"}, secrets={"password": "p"}
    )
    assert (await client.connections.browse("con_1")).data[0]["path"] == "a.mp4"
    await client.automations.create(name="hook", trigger="hook", source={"connection_id": "con_1"})
    assert (await client.automations.trigger("aut_1", paths=["a.mp4"]))["job_ids"] == ["job_9"]
    await client.automations.items("aut_1")
    await client.jobs.deliver("job_1", connection_id="con_1")
    await client.jobs.deliveries("job_1")
    await client.deliveries.retry("dlv_1")
    assert routes(rec) == [
        ("POST", "/v1/connections"),
        ("GET", "/v1/connections/con_1/browse"),
        ("POST", "/v1/automations"),
        ("POST", "/v1/automations/aut_1/trigger"),
        ("GET", "/v1/automations/aut_1/items"),
        ("POST", "/v1/jobs/job_1/deliveries"),
        ("GET", "/v1/jobs/job_1/deliveries"),
        ("POST", "/v1/deliveries/dlv_1/retry"),
    ]
