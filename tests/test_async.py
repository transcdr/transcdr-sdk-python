from __future__ import annotations

import uuid

import httpx
import pytest

from transcdr import APIError, NotFoundError

from .conftest import AsyncRecorder, error_body, json_response

pytestmark = pytest.mark.asyncio

JOB = {"object": "job", "id": "job_1", "status": "queued"}


async def test_async_create_and_retry_with_same_key(make_async_client, sleeps):
    rec = AsyncRecorder(
        json_response(502, error_body("api_error", "bad_gateway", "down")),
        json_response(201, JOB),
    )
    client = make_async_client(rec)
    job = await client.jobs.create(input="https://example.com/in.mp4", preset="hls-av1-abr")
    assert job["id"] == "job_1"
    keys = {r.headers["Idempotency-Key"] for r in rec.requests}
    assert len(keys) == 1 and uuid.UUID(keys.pop())
    assert len(sleeps) == 1
    await client.close()


async def test_async_errors(make_async_client):
    rec = AsyncRecorder(json_response(404, error_body("invalid_request_error", "not_found", "gone")))
    client = make_async_client(rec)
    with pytest.raises(NotFoundError) as info:
        await client.assets.retrieve("ast_x")
    assert info.value.code == "not_found"


async def test_async_post_not_retried_without_key(make_async_client, sleeps):
    rec = AsyncRecorder(json_response(500, error_body("api_error", "internal", "oops")))
    client = make_async_client(rec)
    with pytest.raises(APIError):
        await client.jobs.cancel("job_1")
    assert len(rec.requests) == 1 and sleeps == []


async def test_async_auto_paging(make_async_client):
    def page(ids, cursor):
        return json_response(
            200,
            {"object": "list", "data": [{"id": i} for i in ids], "has_more": cursor is not None, "next_cursor": cursor},
        )

    rec = AsyncRecorder(page(["evt_1", "evt_2"], "evt_2"), page(["evt_3"], None))
    client = make_async_client(rec)
    first = await client.events.list(type="job.completed", limit=2)
    assert first.has_more and first.next_cursor == "evt_2"
    ids = [e["id"] async for e in first.auto_paging_iter()]
    assert ids == ["evt_1", "evt_2", "evt_3"]
    assert rec.requests[1].url.params["cursor"] == "evt_2"
    assert rec.requests[1].url.params["type"] == "job.completed"


async def test_async_upload_file(make_async_client, tmp_path):
    path = tmp_path / "talk.webm"
    path.write_bytes(b"webm-bytes")
    rec = AsyncRecorder(
        json_response(
            201,
            {
                "object": "upload",
                "id": "upl_9",
                "upload_url": "https://storage.test/put",
                "upload_method": "PUT",
                "upload_headers": {"Content-Type": "video/webm"},
            },
        ),
        httpx.Response(200),
        json_response(200, {"object": "asset", "id": "ast_9", "status": "ready"}),
    )
    client = make_async_client(rec)
    asset = await client.uploads.upload_file(str(path))
    assert asset["id"] == "ast_9"
    assert rec.json(0)["content_type"] == "video/webm"
    assert rec.bodies[1] == b"webm-bytes"
    assert rec.requests[1].headers["Content-Length"] == "10"
    assert "Authorization" not in rec.requests[1].headers
    assert rec.requests[2].url.path == "/v1/uploads/upl_9/complete"


async def test_async_wait(make_async_client, monkeypatch):
    import transcdr.resources.jobs as jobs_mod

    async def no_sleep(_):
        return None

    monkeypatch.setattr(jobs_mod.asyncio, "sleep", no_sleep)
    rec = AsyncRecorder(
        json_response(200, {**JOB, "status": "running"}),
        json_response(200, {**JOB, "status": "completed"}),
    )
    client = make_async_client(rec)
    seen = []

    async def on_progress(job):
        seen.append(job["status"])

    job = await client.jobs.wait("job_1", poll_interval=0.01, on_progress=on_progress)
    assert job["status"] == "completed"
    assert seen == ["running", "completed"]
