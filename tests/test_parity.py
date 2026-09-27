"""Organizations, connection and destination checks, SNS/SQS destinations, queue
automations, the input report, announcements, the changelog and the operator
console: the surface shared with the TypeScript SDK."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, List

import pytest

from transcdr import NOT_GIVEN, TranscdrError

from .conftest import API_KEY, BASE_URL, AsyncRecorder, Recorder, json_response

MEMBERSHIP = {
    "object": "membership",
    "organization": {"id": "org_2", "name": "Second", "slug": "second", "plan": "starter"},
    "role": "owner",
    "created_at": "2026-09-27T00:00:00Z",
}
AUTH = {
    "token": "tds_example",
    "user": {"id": "usr_1", "role": "owner", "organization_id": "org_2"},
    "organization": {"id": "org_2"},
    "organizations": [MEMBERSHIP],
}
LIST: Dict[str, Any] = {"object": "list", "data": [], "has_more": False, "next_cursor": None}

# The report in the TypeScript SDK's usage test.
INPUT_REPORT = {
    "object": "input_report",
    "from": "2026-09-01",
    "to": "2026-09-30",
    "unmeasured": 1,
    "kinds": [
        {"kind": "mp4/h264", "container": "mp4", "video_codec": "h264", "files": 2,
         "size_bytes": 22_000_000, "input_minutes": 2.07, "billable_minutes": 4.13},
    ],
    "points": [
        {"kind": "mp4/h264", "files": 2, "size_bytes": 22_000_000, "input_minutes": 2.07,
         "billable_minutes": 4.13, "mean_duration_seconds": 62, "mean_size_bytes": 11_000_000,
         "duration_range": [56.23, 100], "size_range": [10_000_000, 17_782_794]},
    ],
}  # fmt: skip


def body(rec: Recorder, index: int = -1) -> Any:
    raw = rec.bodies[index]
    return json.loads(raw) if raw else None


def path(rec: Recorder, index: int = -1) -> str:
    req = rec.requests[index]
    return f"{req.method} {req.url.raw_path.decode()}"


# --------------------------------------------------------------------------
# Organizations and members
# --------------------------------------------------------------------------


def test_login_with_organization_and_switch(make_client):
    rec = Recorder(json_response(200, AUTH), json_response(200, AUTH))
    client = make_client(rec)
    res = client.auth.login(email="person@example.com", password="pw", organization_id="org_2")
    assert path(rec) == "POST /v1/auth/login"
    assert body(rec) == {"email": "person@example.com", "password": "pw", "organization_id": "org_2"}
    assert res["organizations"][0]["organization"]["slug"] == "second"

    client.auth.switch("org_2")
    assert path(rec) == "POST /v1/auth/switch"
    assert body(rec) == {"organization_id": "org_2"}


def test_login_without_organization_sends_none(make_client):
    rec = Recorder(json_response(200, AUTH))
    make_client(rec).auth.login(email="person@example.com", password="pw")
    assert body(rec) == {"email": "person@example.com", "password": "pw"}


def test_organizations(make_client):
    rec = Recorder(json_response(200, {**LIST, "data": [MEMBERSHIP]}), json_response(201, AUTH))
    client = make_client(rec)
    page = client.organizations.list()
    assert path(rec) == "GET /v1/organizations"
    assert page.data[0]["role"] == "owner"
    res = client.organizations.create(name="Second")
    assert path(rec) == "POST /v1/organizations"
    assert body(rec) == {"name": "Second"}
    assert res["token"] == "tds_example"


def test_members_create_for_existing_and_new_users(make_client):
    rec = Recorder(json_response(201, {"id": "usr_2"}), json_response(201, {"id": "usr_3"}))
    client = make_client(rec)
    client.organization.members.create(email="person@example.com", role="member")
    assert body(rec) == {"email": "person@example.com", "role": "member"}
    client.organization.members.create(email="new@example.com", role="admin", name="New", password="pw")
    assert body(rec) == {"email": "new@example.com", "role": "admin", "name": "New", "password": "pw"}


def test_members_leave(make_client):
    me = {"user": {"id": "usr_1"}, "organization": {"id": "org_1"}, "organizations": [MEMBERSHIP]}
    rec = Recorder(json_response(200, me), json_response(204, None))
    make_client(rec).organization.members.leave()
    assert [path(rec, 0), path(rec, 1)] == ["GET /v1/me", "DELETE /v1/organization/members/usr_1"]


def test_members_leave_refuses_api_keys(make_client):
    # The API reports the key's owner as the user; the api_key field tells them apart.
    me = {"user": {"id": "usr_1"}, "api_key": {"id": "key_1"}, "organizations": []}
    rec = Recorder(json_response(200, me))
    with pytest.raises(TranscdrError):
        make_client(rec).organization.members.leave()
    assert len(rec.requests) == 1


def test_api_keys_revoke_is_delete(make_client):
    rec = Recorder(json_response(204, None))
    make_client(rec).api_keys.revoke("key_1")
    assert path(rec) == "DELETE /v1/api-keys/key_1"


def test_asset_content_url(make_client):
    rec = Recorder(json_response(200, {"url": "https://signed", "expires_at": "2026-09-27T01:00:00Z"}))
    signed = make_client(rec).assets.content_url("ast_1")
    assert path(rec) == "GET /v1/assets/ast_1/content?redirect=false"
    assert signed["expires_at"] == "2026-09-27T01:00:00Z"


# --------------------------------------------------------------------------
# Connections
# --------------------------------------------------------------------------

CHECK = {
    "object": "connection_check",
    "ok": True,
    "steps": [{"id": "list", "label": "List", "status": "passed", "detail": None}],
    "identity": {"provider": "aws", "arn": "arn:aws:iam::123456789012:user/transcdr", "account": "123456789012"},
    "setup": {"iam_policy": {"Version": "2012-10-17"}},
    "roles": {"source": True, "watch_folder": True, "destination": False},
}


def test_connections_enable_disable_check(make_client):
    conn = {"id": "con_1", "enabled": True, "class": "storage", "capabilities": {"trigger": False, "events": False}}
    rec = Recorder(*(json_response(200, x) for x in (conn, conn, conn, CHECK, CHECK)))
    client = make_client(rec)

    client.connections.enable("con_1")
    assert path(rec) == "PATCH /v1/connections/con_1" and body(rec) == {"enabled": True}
    client.connections.disable("con_1")
    assert body(rec) == {"enabled": False}
    client.connections.update("con_1", config={"root": None}, enabled=True)
    assert body(rec) == {"enabled": True, "config": {"root": None}}

    report = client.connections.check(
        kind="s3", config={"bucket": "media", "region": "us-east-1"}, secrets={"access_key_id": "AKIAEXAMPLE"}
    )
    assert path(rec) == "POST /v1/connections/check"
    assert body(rec) == {
        "kind": "s3",
        "config": {"bucket": "media", "region": "us-east-1"},
        "secrets": {"access_key_id": "AKIAEXAMPLE"},
    }
    assert report["roles"]["watch_folder"] is True and report["identity"]["provider"] == "aws"

    client.connections.check_saved("con_1")
    assert path(rec) == "POST /v1/connections/con_1/check"
    assert rec.bodies[-1] == b""


def test_messaging_connection(make_client):
    rec = Recorder(json_response(201, {"id": "con_q", "class": "messaging", "capabilities": {"trigger": True}}))
    conn = make_client(rec).connections.create(
        name="Triggers",
        kind="sqs",
        config={"queue_url": "https://sqs.us-east-1.amazonaws.com/123456789012/uploads"},
        secrets={"access_key_id": "AKIAEXAMPLE", "secret_access_key": "example"},
    )
    assert body(rec)["kind"] == "sqs"
    assert conn["capabilities"]["trigger"] is True


# --------------------------------------------------------------------------
# Event destinations
# --------------------------------------------------------------------------

AWS = {"access_key_id": "AKIAEXAMPLE", "secret_access_key": "example"}


def test_webhook_destinations(make_client):
    rec = Recorder(*(json_response(201, {"id": "whk_1", "secret": "whsec_example"}) for _ in range(4)))
    client = make_client(rec)

    client.webhooks.create(url="https://example.com/hooks", events=["job.completed"])
    assert body(rec) == {"url": "https://example.com/hooks", "events": ["job.completed"]}

    client.webhooks.create(topic_arn="arn:aws:sns:us-east-1:123456789012:events", aws=AWS)
    assert body(rec) == {"type": "sns", "topic_arn": "arn:aws:sns:us-east-1:123456789012:events", "aws": AWS}

    client.webhooks.create(
        queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/events.fifo",
        aws={**AWS, "message_group_id": "jobs"},
        description="FIFO",
    )
    assert body(rec)["type"] == "sqs" and body(rec)["aws"]["message_group_id"] == "jobs"

    client.webhooks.create(connection_id="con_q", events=["*"])
    assert body(rec) == {"connection_id": "con_q", "events": ["*"]}


def test_webhook_create_needs_exactly_one_target(make_client):
    client = make_client(Recorder())
    with pytest.raises(TypeError):
        client.webhooks.create(events=["*"])
    with pytest.raises(TypeError):
        client.webhooks.create(url="https://example.com", connection_id="con_1")


def test_webhook_update_aws_nulls_and_checks(make_client):
    rec = Recorder(*(json_response(200, {"id": "whk_1", "object": "webhook_check"}) for _ in range(3)))
    client = make_client(rec)
    client.webhooks.update("whk_1", aws={"access_key_id": "AKIAEXAMPLE", "endpoint": None, "message_group_id": None})
    assert path(rec) == "PATCH /v1/webhooks/whk_1"
    assert body(rec) == {"aws": {"access_key_id": "AKIAEXAMPLE", "endpoint": None, "message_group_id": None}}

    client.webhooks.check(url="https://example.com/hooks")
    assert path(rec) == "POST /v1/webhooks/check" and body(rec) == {"url": "https://example.com/hooks"}
    client.webhooks.check_saved("whk_1")
    assert path(rec) == "POST /v1/webhooks/whk_1/check"


# --------------------------------------------------------------------------
# Queue automations
# --------------------------------------------------------------------------


def test_queue_automation(make_client):
    run = {"object": "automation_run", "jobs_created": 1, "messages_received": 2, "messages_deleted": 2}
    rec = Recorder(json_response(201, {"id": "aut_1", "trigger": "queue"}), json_response(200, run),
                   json_response(200, {"id": "aut_1"}))  # fmt: skip
    client = make_client(rec)
    client.automations.create(
        name="Uploads",
        trigger="queue",
        trigger_connection_id="con_q",
        source={"connection_id": "con_s", "prefix": "incoming/"},
    )
    assert body(rec) == {
        "name": "Uploads",
        "trigger": "queue",
        "trigger_connection_id": "con_q",
        "source": {"connection_id": "con_s", "prefix": "incoming/"},
    }
    result = client.automations.run("aut_1")
    assert result["messages_deleted"] == 2
    client.automations.update("aut_1", trigger_connection_id="", preset="", output={}, metadata={})
    assert body(rec) == {"trigger_connection_id": "", "preset": "", "output": {}, "metadata": {}}


# --------------------------------------------------------------------------
# Constant bit rate
# --------------------------------------------------------------------------


def test_cbr_preset(make_client):
    output = {
        "mode": "hls",
        "codec": "h264",
        "quality": {"target": "cbr", "bitrate": "3M", "buffer_ms": 1500},
        "renditions": [{"width": 1920, "height": 1080, "bitrate": "6M"}, {"width": 1280, "height": 720}],
    }
    rec = Recorder(json_response(201, {"id": "pre_1", "output": output}))
    preset = make_client(rec).presets.create(name="Broadcast CBR", output=output)
    assert path(rec) == "POST /v1/presets"
    assert body(rec)["output"] == output
    assert preset["output"]["quality"]["target"] == "cbr"


# --------------------------------------------------------------------------
# Usage: the input report
# --------------------------------------------------------------------------


def test_usage_inputs(make_client):
    rec = Recorder(json_response(200, INPUT_REPORT), json_response(200, INPUT_REPORT))
    client = make_client(rec)
    report = client.usage.inputs(from_="2026-09-01", to=dt.date(2026, 9, 30))
    assert path(rec) == "GET /v1/usage/inputs?from=2026-09-01&to=2026-09-30"
    assert report["points"][0]["mean_duration_seconds"] == 62
    assert report["kinds"][0]["kind"] == "mp4/h264"
    assert report["unmeasured"] == 1

    client.usage.inputs()
    assert path(rec) == "GET /v1/usage/inputs"


# --------------------------------------------------------------------------
# Announcements and the changelog
# --------------------------------------------------------------------------

ANNOUNCEMENT = {"object": "announcement", "id": "ann_1", "kind": "changelog", "seen": False, "credit": None}


def test_announcements(make_client):
    rec = Recorder(json_response(200, {**LIST, "data": [ANNOUNCEMENT]}), json_response(204, None),
                   json_response(204, None))  # fmt: skip
    client = make_client(rec)
    page = client.announcements.list(unseen=True, kind="service_credit", limit=5)
    assert path(rec) == "GET /v1/announcements?unseen=true&kind=service_credit&limit=5"
    assert page.data[0]["id"] == "ann_1"

    client.announcements.mark_seen([])
    assert len(rec.requests) == 1  # nothing to send
    client.announcements.mark_seen(["ann_1"])
    assert path(rec) == "POST /v1/announcements/seen" and body(rec) == {"ids": ["ann_1"]}
    client.announcements.mark_all_seen()
    assert body(rec) == {"all": True}


def test_announcements_list_all(make_client):
    rec = Recorder(json_response(200, LIST))
    make_client(rec).announcements.list()
    assert path(rec) == "GET /v1/announcements"


def test_changelog_is_public_and_paginated(make_client, monkeypatch):
    monkeypatch.delenv("TRANSCDR_API_KEY", raising=False)
    first = {"object": "list", "data": [ANNOUNCEMENT], "has_more": True, "next_cursor": "ann_1"}
    second = {**LIST, "data": [{**ANNOUNCEMENT, "id": "ann_0"}]}
    rec = Recorder(json_response(200, first), json_response(200, second))
    client = make_client(rec, api_key=None)
    ids = [a["id"] for a in client.changelog.list(limit=1).auto_paging_iter()]
    assert ids == ["ann_1", "ann_0"]
    assert path(rec, 1) == "GET /v1/changelog?limit=1&cursor=ann_1"
    assert "Authorization" not in rec.requests[0].headers


# --------------------------------------------------------------------------
# The operator console
# --------------------------------------------------------------------------


def test_admin(make_client):
    responses: List[Any] = [
        {"object": "admin_overview", "organizations": 3, "jobs_by_status": {"queued": 1}},
        {**LIST, "data": [{"id": "job_1", "organization": "org_1", "internals": None}]},
        {**LIST, "data": [{"id": "org_1"}]},
        {"id": "org_1", "plan": "growth"},
        {"object": "billing"},
    ]
    rec = Recorder(*(json_response(200, r) for r in responses))
    admin = make_client(rec).admin
    assert admin.overview()["organizations"] == 3
    admin.jobs(status="failed", limit=10)
    assert path(rec) == "GET /v1/admin/jobs?status=failed&limit=10"
    admin.organizations()
    assert path(rec) == "GET /v1/admin/organizations"
    admin.update_organization("org_1", plan="growth", suspended=False)
    assert path(rec) == "PATCH /v1/admin/organizations/org_1"
    assert body(rec) == {"plan": "growth", "suspended": False}
    admin.grant_credit("org_1", amount_cents=5000, description="Goodwill", expires_in_days=30)
    assert path(rec) == "POST /v1/admin/organizations/org_1/credit"
    assert body(rec) == {"amount_cents": 5000, "description": "Goodwill", "expires_in_days": 30}


def test_admin_announcements(make_client):
    rec = Recorder(*(json_response(200, ANNOUNCEMENT) for _ in range(4)), json_response(204, None))
    announcements = make_client(rec).admin.announcements
    announcements.create(title="New", body="**Bold**")
    assert path(rec) == "POST /v1/admin/announcements" and body(rec) == {"title": "New", "body": "**Bold**"}
    announcements.create(title="Draft", body="Soon", published_at=None, link={"label": "Try", "url": "/app"})
    assert body(rec) == {"title": "Draft", "body": "Soon", "link": {"label": "Try", "url": "/app"}, "published_at": None}
    announcements.update("ann_1", link=None, published_at=dt.datetime(2026, 10, 1, 9, 0))
    assert path(rec) == "PATCH /v1/admin/announcements/ann_1"
    assert body(rec) == {"link": None, "published_at": "2026-10-01T09:00:00+00:00"}
    announcements.update("ann_1", tags=["integrations"], title=NOT_GIVEN)
    assert body(rec) == {"tags": ["integrations"]}
    announcements.delete("ann_1")
    assert path(rec) == "DELETE /v1/admin/announcements/ann_1"


def test_admin_incidents(make_client):
    incident = {"object": "incident", "id": "inc_1", "status": "draft"}
    rec = Recorder(json_response(200, {**LIST, "data": [{"name": "dropped_audio"}]}), json_response(200, LIST),
                   *(json_response(200, incident) for _ in range(4)))  # fmt: skip
    incidents = make_client(rec).admin.incidents
    assert incidents.detectors().data[0]["name"] == "dropped_audio"
    assert path(rec) == "GET /v1/admin/incident-detectors"
    incidents.list()
    assert path(rec) == "GET /v1/admin/incidents"
    incidents.create(
        title="Dropped audio",
        description="Some outputs had no audio.",
        window_start=dt.datetime(2026, 9, 20, tzinfo=dt.timezone.utc),
        detector="dropped_audio",
        multiplier=3,
    )
    assert body(rec) == {
        "title": "Dropped audio",
        "description": "Some outputs had no audio.",
        "window_start": "2026-09-20T00:00:00+00:00",
        "detector": "dropped_audio",
        "multiplier": 3,
    }
    incidents.retrieve("inc_1")
    assert path(rec) == "GET /v1/admin/incidents/inc_1"
    incidents.preview("inc_1")
    assert path(rec) == "POST /v1/admin/incidents/inc_1/preview"
    incidents.apply("inc_1", include_review=True)
    assert path(rec) == "POST /v1/admin/incidents/inc_1/apply" and body(rec) == {"include_review": True}


# --------------------------------------------------------------------------
# Async twins
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_parity(make_async_client):
    me = {"user": {"id": "usr_1"}, "organization": {"id": "org_1"}, "organizations": [MEMBERSHIP]}
    rec = AsyncRecorder(
        json_response(200, AUTH),  # switch
        json_response(200, {**LIST, "data": [MEMBERSHIP]}),  # organizations.list
        json_response(201, AUTH),  # organizations.create
        json_response(200, me),  # leave: me
        json_response(204, None),  # leave: delete
        json_response(200, {"url": "https://signed", "expires_at": "t"}),  # content_url
        json_response(200, {"id": "con_1"}),  # enable
        json_response(200, CHECK),  # check
        json_response(200, CHECK),  # check_saved
        json_response(201, {"id": "whk_1"}),  # webhooks.create sns
        json_response(200, {"object": "webhook_check"}),  # webhooks.check_saved
        json_response(200, INPUT_REPORT),  # usage.inputs
        json_response(200, LIST),  # announcements.list
        json_response(204, None),  # mark_all_seen
        json_response(200, LIST),  # changelog
        json_response(200, {"object": "admin_overview"}),  # admin.overview
        json_response(200, {"object": "billing"}),  # grant_credit
        json_response(200, ANNOUNCEMENT),  # admin announcement draft
        json_response(200, {"id": "inc_1"}),  # incidents.apply
    )
    client = make_async_client(rec)
    await client.auth.switch("org_2")
    assert body(rec, 0) == {"organization_id": "org_2"}
    assert (await client.organizations.list()).data[0]["role"] == "owner"
    await client.organizations.create(name="Second")
    await client.organization.members.leave()
    assert path(rec) == "DELETE /v1/organization/members/usr_1"
    await client.assets.content_url("ast_1")
    assert path(rec) == "GET /v1/assets/ast_1/content?redirect=false"
    await client.connections.enable("con_1")
    assert body(rec) == {"enabled": True}
    await client.connections.check(kind="sftp", config={"host": "files.example.com"})
    assert path(rec) == "POST /v1/connections/check"
    await client.connections.check_saved("con_1")
    await client.webhooks.create(topic_arn="arn:aws:sns:us-east-1:123456789012:events", aws=AWS)
    assert body(rec)["type"] == "sns"
    await client.webhooks.check_saved("whk_1")
    assert path(rec) == "POST /v1/webhooks/whk_1/check"
    report = await client.usage.inputs(from_="2026-09-01")
    assert path(rec) == "GET /v1/usage/inputs?from=2026-09-01" and report["kinds"][0]["files"] == 2
    await client.announcements.list(unseen=True)
    assert path(rec) == "GET /v1/announcements?unseen=true"
    await client.announcements.mark_seen([])
    await client.announcements.mark_all_seen()
    assert body(rec) == {"all": True}
    await client.changelog.list()
    assert path(rec) == "GET /v1/changelog"
    await client.admin.overview()
    await client.admin.grant_credit("org_1", amount_cents=-100)
    assert body(rec) == {"amount_cents": -100}
    await client.admin.announcements.create(title="Draft", body="Soon", published_at=None)
    assert body(rec) == {"title": "Draft", "body": "Soon", "published_at": None}
    await client.admin.incidents.apply("inc_1")
    assert body(rec) == {"include_review": False}
    assert len(rec.requests) == len(rec.bodies) == 19
    await client.close()


def test_new_clients_are_wired():
    from transcdr import AsyncTranscdr, Transcdr

    for cls in (Transcdr, AsyncTranscdr):
        client = cls(api_key=API_KEY, base_url=BASE_URL)
        for name in ("organizations", "announcements", "changelog", "admin"):
            assert hasattr(client, name), name
        assert hasattr(client.admin, "incidents") and hasattr(client.admin, "announcements")
