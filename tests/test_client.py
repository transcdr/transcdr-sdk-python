from __future__ import annotations

import io
import uuid
from urllib.parse import parse_qsl

import httpx
import pytest

import transcdr
from transcdr import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    InvalidRequestError,
    NotFoundError,
    PermissionDeniedError,
    QuotaError,
    RateLimitError,
    TranscdrError,
    WaitTimeoutError,
)

from .conftest import API_KEY, BASE_URL, Recorder, error_body, json_response

JOB = {"object": "job", "id": "job_1", "status": "queued"}


def query(request: httpx.Request) -> list:
    return parse_qsl(request.url.query.decode(), keep_blank_values=True)


# --------------------------------------------------------------------------
# Basics
# --------------------------------------------------------------------------


def test_sends_auth_and_user_agent(make_client):
    rec = Recorder(json_response(200, JOB))
    client = make_client(rec)
    job = client.jobs.retrieve("job_1")
    assert job["id"] == "job_1"
    req = rec.requests[0]
    assert req.method == "GET"
    assert str(req.url) == f"{BASE_URL}/v1/jobs/job_1"
    assert req.headers["Authorization"] == f"Bearer {API_KEY}"
    assert req.headers["User-Agent"].startswith("transcdr-python/")


def test_env_defaults(monkeypatch):
    monkeypatch.setenv("TRANSCDR_API_KEY", "tdk_live_fromenv")
    monkeypatch.setenv("TRANSCDR_BASE_URL", "http://localhost:8080/")
    client = transcdr.Transcdr()
    assert client.api_key == "tdk_live_fromenv"
    assert client.base_url == "http://localhost:8080"
    assert client.livemode is True
    client.close()


def test_default_base_url(monkeypatch):
    monkeypatch.delenv("TRANSCDR_BASE_URL", raising=False)
    client = transcdr.Transcdr(api_key="tdk_test_x")
    assert client.base_url == "https://api.transcdr.io"
    assert client.livemode is False
    client.close()


def test_no_auth_header_without_key(make_client, monkeypatch):
    monkeypatch.delenv("TRANSCDR_API_KEY", raising=False)
    rec = Recorder(json_response(200, {"object": "list", "data": [], "has_more": False}))
    client = make_client(rec, api_key=None)
    client.plans.list()
    assert "Authorization" not in rec.requests[0].headers


def test_path_segments_are_encoded(make_client):
    rec = Recorder(json_response(200, {"url": "https://signed", "expires_at": "t"}))
    make_client(rec).jobs.output_url("job_1", "1080p/../x")
    assert rec.requests[0].url.raw_path == b"/v1/jobs/job_1/outputs/1080p%2F..%2Fx?redirect=false"


def test_delete_returns_none_on_204(make_client):
    rec = Recorder(httpx.Response(204))
    assert make_client(rec).jobs.delete("job_1") is None
    assert rec.requests[0].method == "DELETE"


def test_redirect_is_returned_as_url(make_client):
    rec = Recorder(httpx.Response(302, headers={"Location": "https://cdn/signed"}))
    assert make_client(rec).assets.download_url("ast_1") == "https://cdn/signed"


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status,type_,cls",
    [
        (400, "invalid_request_error", InvalidRequestError),
        (401, "authentication_error", AuthenticationError),
        (402, "quota_error", QuotaError),
        (403, "permission_error", PermissionDeniedError),
        (404, "invalid_request_error", NotFoundError),
        (409, "invalid_request_error", InvalidRequestError),
        (422, "invalid_request_error", InvalidRequestError),
        (429, "rate_limit_error", RateLimitError),
        (500, "api_error", APIError),
    ],
)
def test_error_mapping(make_client, status, type_, cls):
    rec = Recorder(json_response(status, error_body(type_, "some_code", "boom", request_id="req_1")))
    client = make_client(rec, max_retries=0)
    with pytest.raises(cls) as info:
        client.jobs.retrieve("job_1")
    err = info.value
    assert isinstance(err, TranscdrError)
    assert err.status == status
    assert err.type == type_
    assert err.code == "some_code"
    assert err.message == "boom"
    assert err.request_id == "req_1"


def test_validation_error_fields(make_client):
    body = error_body(
        "invalid_request_error",
        "validation_failed",
        "The output.renditions field is required.",
        param="output.renditions",
        details={"output.renditions": ["The output.renditions field is required."]},
        request_id="3f2a-1c",
    )
    rec = Recorder(json_response(422, body))
    with pytest.raises(InvalidRequestError) as info:
        make_client(rec).jobs.create(input="https://x/in.mp4", output={"renditions": []})
    err = info.value
    assert err.param == "output.renditions"
    assert err.details == {"output.renditions": ["The output.renditions field is required."]}
    assert "validation_failed" in str(err) and "3f2a-1c" in str(err)


def test_insufficient_scope(make_client):
    rec = Recorder(json_response(403, error_body("permission_error", "insufficient_scope", "nope")))
    with pytest.raises(PermissionDeniedError) as info:
        make_client(rec).billing.retrieve()
    assert info.value.code == "insufficient_scope"


def test_request_id_from_header_and_non_json_body(make_client):
    rec = Recorder(httpx.Response(502, text="Bad Gateway", headers={"X-Request-Id": "req_hdr"}))
    with pytest.raises(APIError) as info:
        make_client(rec, max_retries=0).status.retrieve()
    assert info.value.request_id == "req_hdr"
    assert info.value.message == "Bad Gateway"


def test_rate_limit_retry_after(make_client):
    rec = Recorder(
        json_response(429, error_body("rate_limit_error", "rate_limited", "slow"), {"Retry-After": "7"})
    )
    with pytest.raises(RateLimitError) as info:
        make_client(rec, max_retries=0).jobs.list()
    assert info.value.retry_after == 7.0


# --------------------------------------------------------------------------
# Retries
# --------------------------------------------------------------------------


def test_get_retries_on_5xx_then_succeeds(make_client, sleeps):
    rec = Recorder(
        json_response(503, error_body("api_error", "unavailable", "down")),
        json_response(500, error_body("api_error", "internal", "oops")),
        json_response(200, JOB),
    )
    assert make_client(rec).jobs.retrieve("job_1")["id"] == "job_1"
    assert len(rec.requests) == 3
    assert len(sleeps) == 2
    # Exponential backoff with jitter: attempt 0 in (0.375, 0.5], attempt 1 in (0.75, 1.0].
    assert 0.375 <= sleeps[0] <= 0.5
    assert 0.75 <= sleeps[1] <= 1.0


def test_retry_honours_retry_after(make_client, sleeps):
    rec = Recorder(
        json_response(429, error_body("rate_limit_error", "rate_limited", "slow"), {"Retry-After": "3"}),
        json_response(200, JOB),
    )
    make_client(rec).jobs.retrieve("job_1")
    assert sleeps == [3.0]


def test_retries_exhausted_raises_last_error(make_client, sleeps):
    rec = Recorder(*[json_response(500, error_body("api_error", "internal", "oops")) for _ in range(3)])
    with pytest.raises(APIError):
        make_client(rec, max_retries=2).jobs.retrieve("job_1")
    assert len(rec.requests) == 3
    assert len(sleeps) == 2


def test_connection_error_is_retried(make_client, sleeps):
    rec = Recorder(httpx.ConnectError("refused"), json_response(200, JOB))
    assert make_client(rec).jobs.retrieve("job_1")["id"] == "job_1"
    assert len(sleeps) == 1


def test_connection_error_raised_after_retries(make_client):
    rec = Recorder(*[httpx.ConnectError("refused") for _ in range(3)])
    with pytest.raises(APIConnectionError):
        make_client(rec).jobs.retrieve("job_1")
    assert len(rec.requests) == 3


def test_timeout_maps_to_timeout_error(make_client):
    rec = Recorder(httpx.ReadTimeout("slow"))
    with pytest.raises(APITimeoutError):
        make_client(rec, max_retries=0).jobs.retrieve("job_1")


def test_4xx_is_not_retried(make_client, sleeps):
    rec = Recorder(json_response(404, error_body("invalid_request_error", "not_found", "no")))
    with pytest.raises(NotFoundError):
        make_client(rec).jobs.retrieve("job_x")
    assert len(rec.requests) == 1 and sleeps == []


def test_post_without_idempotency_key_is_not_retried(make_client, sleeps):
    rec = Recorder(json_response(503, error_body("api_error", "unavailable", "down")))
    with pytest.raises(APIError):
        make_client(rec).jobs.cancel("job_1")
    assert len(rec.requests) == 1 and sleeps == []
    assert "Idempotency-Key" not in rec.requests[0].headers


def test_post_connection_error_without_key_is_not_retried(make_client):
    rec = Recorder(httpx.ConnectError("reset"))
    with pytest.raises(APIConnectionError):
        make_client(rec).webhooks.test("whk_1")
    assert len(rec.requests) == 1


def test_max_retries_zero(make_client):
    rec = Recorder(json_response(503, error_body("api_error", "unavailable", "down")))
    with pytest.raises(APIError):
        make_client(rec, max_retries=0).jobs.retrieve("job_1")
    assert len(rec.requests) == 1


def test_with_options_overrides_retries(make_client):
    rec = Recorder(json_response(503, error_body("api_error", "unavailable", "down")))
    client = make_client(rec, max_retries=5)
    with pytest.raises(APIError):
        client.with_options(max_retries=0).jobs.retrieve("job_1")
    assert len(rec.requests) == 1


# --------------------------------------------------------------------------
# Idempotency
# --------------------------------------------------------------------------


def test_jobs_create_sends_generated_idempotency_key(make_client):
    rec = Recorder(json_response(201, JOB))
    make_client(rec).jobs.create(input="https://example.com/in.mp4", preset="hls-av1-abr")
    key = rec.requests[0].headers["Idempotency-Key"]
    assert uuid.UUID(key).version == 4
    assert rec.json() == {
        "input": {"type": "url", "url": "https://example.com/in.mp4"},
        "preset": "hls-av1-abr",
    }


def test_jobs_create_retry_reuses_same_key(make_client, sleeps):
    rec = Recorder(
        json_response(503, error_body("api_error", "unavailable", "down")),
        httpx.ConnectError("reset"),
        json_response(201, JOB, {"Idempotent-Replayed": "true"}),
    )
    job = make_client(rec).jobs.create(input={"type": "asset", "asset_id": "ast_1"})
    assert job["id"] == "job_1"
    keys = {r.headers["Idempotency-Key"] for r in rec.requests}
    assert len(rec.requests) == 3 and len(keys) == 1
    assert len(sleeps) == 2


def test_each_create_gets_a_fresh_key(make_client):
    rec = Recorder(json_response(201, JOB), json_response(201, JOB))
    client = make_client(rec)
    client.jobs.create(input="ast_1")
    client.jobs.create(input="ast_1")
    assert rec.requests[0].headers["Idempotency-Key"] != rec.requests[1].headers["Idempotency-Key"]
    assert rec.json(0)["input"] == {"type": "asset", "asset_id": "ast_1"}


def test_explicit_idempotency_key(make_client):
    rec = Recorder(json_response(201, {"object": "upload", "id": "upl_1"}))
    make_client(rec).uploads.create(
        filename="a.mp4", content_type="video/mp4", size_bytes=3, idempotency_key="my-key"
    )
    assert rec.requests[0].headers["Idempotency-Key"] == "my-key"


def test_uploads_create_sends_generated_key(make_client):
    rec = Recorder(json_response(201, {"object": "upload", "id": "upl_1"}))
    make_client(rec).uploads.create(filename="a.mp4", content_type="video/mp4", size_bytes=3)
    assert uuid.UUID(rec.requests[0].headers["Idempotency-Key"])


# --------------------------------------------------------------------------
# Pagination
# --------------------------------------------------------------------------


def page(ids, cursor):
    return json_response(
        200,
        {
            "object": "list",
            "data": [{"object": "job", "id": i, "status": "completed"} for i in ids],
            "has_more": cursor is not None,
            "next_cursor": cursor,
        },
    )


def test_list_returns_page(make_client):
    rec = Recorder(page(["job_a", "job_b"], "job_b"))
    result = make_client(rec).jobs.list(status="completed", limit=2)
    assert [j["id"] for j in result.data] == ["job_a", "job_b"]
    assert result.has_more is True
    assert result.next_cursor == "job_b"
    assert query(rec.requests[0]) == [("status", "completed"), ("limit", "2")]


def test_auto_paging_iter_walks_all_pages(make_client):
    rec = Recorder(page(["job_a", "job_b"], "job_b"), page(["job_c", "job_d"], "job_d"), page(["job_e"], None))
    first = make_client(rec).jobs.list(status="completed", limit=2)
    ids = [j["id"] for j in first.auto_paging_iter()]
    assert ids == ["job_a", "job_b", "job_c", "job_d", "job_e"]
    assert len(rec.requests) == 3
    assert query(rec.requests[1]) == [("status", "completed"), ("limit", "2"), ("cursor", "job_b")]
    assert query(rec.requests[2]) == [("status", "completed"), ("limit", "2"), ("cursor", "job_d")]


def test_auto_paging_iter_is_lazy(make_client):
    rec = Recorder(page(["job_a", "job_b"], "job_b"), page(["job_c"], None))
    it = make_client(rec).jobs.list().auto_paging_iter()
    assert next(it)["id"] == "job_a"
    assert len(rec.requests) == 1


def test_last_page(make_client):
    rec = Recorder(page(["job_a"], None))
    result = make_client(rec).jobs.list()
    assert result.has_more is False
    assert result.next_page() is None
    assert list(result) == result.data


def test_metadata_filter_encoding(make_client):
    rec = Recorder(page([], None))
    make_client(rec).jobs.list(metadata={"customer": "42"}, created_after="2026-09-01T00:00:00Z")
    assert query(rec.requests[0]) == [
        ("created_after", "2026-09-01T00:00:00Z"),
        ("metadata[customer]", "42"),
    ]


# --------------------------------------------------------------------------
# Uploads
# --------------------------------------------------------------------------


def upload_flow(content_type="video/mp4"):
    return Recorder(
        json_response(
            201,
            {
                "object": "upload",
                "id": "upl_1",
                "asset_id": "ast_1",
                "status": "pending",
                "upload_url": "https://storage.test/bucket/key?X-Amz-Signature=abc",
                "upload_method": "PUT",
                "upload_headers": {"Content-Type": content_type, "x-amz-meta-org": "org_1"},
            },
        ),
        httpx.Response(200),
        json_response(200, {"object": "asset", "id": "ast_1", "status": "ready"}),
    )


def test_upload_file_from_path(make_client, tmp_path):
    path = tmp_path / "clip.mp4"
    data = b"\x00\x01video-bytes" * 1000
    path.write_bytes(data)
    rec = upload_flow()
    progress = []
    asset = make_client(rec).uploads.upload_file(
        path, on_progress=lambda sent, total: progress.append((sent, total))
    )
    assert asset["id"] == "ast_1" and asset["status"] == "ready"

    create, put, complete = rec.requests
    assert (create.method, create.url.path) == ("POST", "/v1/uploads")
    assert rec.json(0) == {"filename": "clip.mp4", "content_type": "video/mp4", "size_bytes": len(data)}
    assert "Idempotency-Key" in create.headers

    assert put.method == "PUT"
    assert str(put.url) == "https://storage.test/bucket/key?X-Amz-Signature=abc"
    assert rec.bodies[1] == data
    assert put.headers["Content-Length"] == str(len(data))
    assert "Transfer-Encoding" not in put.headers
    assert put.headers["x-amz-meta-org"] == "org_1"
    assert "Authorization" not in put.headers  # presigned URLs must not carry the API key

    assert (complete.method, complete.url.path) == ("POST", "/v1/uploads/upl_1/complete")
    assert progress[-1] == (len(data), len(data))


def test_upload_file_from_fileobj(make_client):
    rec = upload_flow("video/quicktime")
    buf = io.BytesIO(b"XXXXmovie")
    buf.seek(4)  # uploads from the current position
    make_client(rec).uploads.upload_file(buf, filename="keynote.mov")
    assert rec.json(0) == {"filename": "keynote.mov", "content_type": "video/quicktime", "size_bytes": 5}
    assert rec.bodies[1] == b"movie"


def test_upload_put_retry_rewinds(make_client, sleeps):
    rec = upload_flow()
    rec.responses.insert(1, httpx.Response(503, text="SlowDown"))
    make_client(rec).uploads.upload_file(b"abcdef", filename="a.mp4")
    assert rec.bodies[1] == rec.bodies[2] == b"abcdef"
    assert len(sleeps) == 1


def test_upload_put_failure(make_client):
    rec = upload_flow()
    rec.responses[1] = httpx.Response(403, text="<Error>SignatureDoesNotMatch</Error>")
    with pytest.raises(APIError) as info:
        make_client(rec).uploads.upload_file(b"abc", filename="a.mp4")
    assert info.value.status == 403
    assert "SignatureDoesNotMatch" in info.value.message


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------


def test_wait_polls_until_terminal(make_client, monkeypatch):
    naps = []
    monkeypatch.setattr(transcdr.resources.jobs.time, "sleep", naps.append)
    rec = Recorder(
        json_response(200, {**JOB, "status": "running", "progress": {"percent": 10}}),
        json_response(200, {**JOB, "status": "running", "progress": {"percent": 80}}),
        json_response(200, {**JOB, "status": "completed", "progress": {"percent": 100}}),
    )
    seen = []
    job = make_client(rec).jobs.wait("job_1", poll_interval=0.5, on_progress=lambda j: seen.append(j["progress"]["percent"]))
    assert job["status"] == "completed"
    assert seen == [10, 80, 100]
    assert naps == [0.5, 0.5]


def test_wait_returns_failed_job(make_client):
    rec = Recorder(json_response(200, {**JOB, "status": "failed", "error": {"code": "decode_failed"}}))
    assert make_client(rec).jobs.wait("job_1")["status"] == "failed"


def test_wait_timeout(make_client):
    rec = Recorder(json_response(200, {**JOB, "status": "running"}))
    with pytest.raises(WaitTimeoutError) as info:
        make_client(rec).jobs.wait("job_1", timeout=0)
    assert info.value.job["status"] == "running"


def test_job_actions(make_client):
    rec = Recorder(
        json_response(200, {**JOB, "status": "canceled"}),
        json_response(200, {**JOB, "status": "queued"}),
        json_response(200, {"url": "https://signed/master.m3u8", "expires_at": "t"}),
    )
    client = make_client(rec)
    client.jobs.cancel("job_1")
    client.jobs.retry("job_1")
    client.jobs.file_url("job_1", "1080p/index.m3u8")
    assert [(r.method, r.url.path) for r in rec.requests] == [
        ("POST", "/v1/jobs/job_1/cancel"),
        ("POST", "/v1/jobs/job_1/retry"),
        ("GET", "/v1/jobs/job_1/files/1080p/index.m3u8"),
    ]


def test_probe_wait(make_client):
    rec = Recorder(json_response(200, {**JOB, "kind": "probe", "input_info": {"width": 1920}}))
    job = make_client(rec).probe.create(input="https://x/in.mp4", wait=True)
    assert job["input_info"]["width"] == 1920
    assert query(rec.requests[0]) == [("wait", "true")]


def test_misc_routes(make_client):
    rec = Recorder(
        json_response(200, {"object": "usage"}),
        json_response(200, {"object": "billing"}),
        page([], None),
        json_response(200, {"object": "user", "id": "usr_1"}),
        json_response(200, {"object": "webhook_delivery", "id": "whd_1"}),
    )
    client = make_client(rec)
    client.usage.retrieve(from_="2026-09-01", to="2026-09-30", granularity="day")
    client.billing.change_plan("growth")
    client.billing.invoices.list()
    client.organization.members.update("usr_1", role="admin")
    client.webhooks.redeliver("whd_1")
    assert query(rec.requests[0]) == [("from", "2026-09-01"), ("to", "2026-09-30"), ("granularity", "day")]
    assert [(r.method, r.url.path) for r in rec.requests[1:]] == [
        ("PUT", "/v1/billing/plan"),
        ("GET", "/v1/billing/invoices"),
        ("PATCH", "/v1/organization/members/usr_1"),
        ("POST", "/v1/webhook-deliveries/whd_1/redeliver"),
    ]
    assert rec.json(1) == {"plan": "growth"}
    assert rec.json(3) == {"role": "admin"}



def test_billing_checkout_portal_settings_and_ledger(make_client):
    rec = Recorder(
        json_response(200, {"object": "checkout", "url": "https://pay.test/s", "changed": False}),
        json_response(200, {"object": "checkout", "url": "https://pay.test/c", "changed": False}),
        json_response(200, {"object": "portal", "url": "https://pay.test/p"}),
        json_response(200, {"object": "billing", "account": {"available_usd": 12.5}}),
        json_response(200, {"object": "billing"}),
        json_response(
            200,
            {
                "object": "list",
                "data": [{"object": "credit_transaction", "id": "ctx_1", "kind": "usage", "amount_usd": -0.25}],
                "has_more": False,
                "next_cursor": None,
            },
        ),
    )
    client = make_client(rec)
    assert client.billing.checkout(plan="growth")["url"] == "https://pay.test/s"
    assert client.billing.checkout(credit_cents=5000)["url"] == "https://pay.test/c"
    assert client.billing.portal()["url"] == "https://pay.test/p"
    summary = client.billing.update_settings(
        monthly_limit_cents=None, auto_recharge={"enabled": True, "threshold_cents": 1000, "amount_cents": 5000}
    )
    assert summary["account"]["available_usd"] == 12.5
    client.billing.update_settings(auto_recharge={"enabled": False})
    ledger = client.billing.transactions(limit=10)
    assert ledger.data[0]["amount_usd"] == -0.25
    assert [(r.method, r.url.path) for r in rec.requests] == [
        ("POST", "/v1/billing/checkout"),
        ("POST", "/v1/billing/checkout"),
        ("POST", "/v1/billing/portal"),
        ("PUT", "/v1/billing/settings"),
        ("PUT", "/v1/billing/settings"),
        ("GET", "/v1/billing/transactions"),
    ]
    assert rec.json(0) == {"plan": "growth"}
    assert rec.json(1) == {"credit_cents": 5000}
    # ``None`` clears the limit; leaving it out leaves it alone.
    assert rec.json(3) == {
        "monthly_limit_cents": None,
        "auto_recharge": {"enabled": True, "threshold_cents": 1000, "amount_cents": 5000},
    }
    assert rec.json(4) == {"auto_recharge": {"enabled": False}}
    assert query(rec.requests[5]) == [("limit", "10")]


def test_billing_checkout_needs_exactly_one_of_plan_or_credit(make_client):
    client = make_client(Recorder())
    with pytest.raises(ValueError):
        client.billing.checkout()
    with pytest.raises(ValueError):
        client.billing.checkout(plan="growth", credit_cents=5000)


def test_job_cost_cap_and_credit_errors(make_client):
    rec = Recorder(json_response(402, error_body("quota_error", "insufficient_credit", "Not enough credit.")))
    with pytest.raises(QuotaError) as info:
        make_client(rec).jobs.create(input="ast_1", max_cost_cents=150)
    assert info.value.code == "insufficient_credit"
    assert rec.json(0)["max_cost_cents"] == 150


STATS = {
    "object": "stats",
    "since": "2026-01-01T00:00:00Z",
    "updated_at": "2026-09-26T12:00:00Z",
    "totals": {
        "jobs_completed": 1200,
        "output_minutes": 83421.5,
        "source_minutes": 30110.0,
        "bytes_delivered": 987654321,
        "renditions_delivered": 4800,
        "customers": 57,
    },
    "last_24h": {"jobs_completed": 42, "output_minutes": 310.2},
    "daily": [{"date": "2026-09-25", "jobs_completed": 40, "output_minutes": 300.0}],
}


def test_stats_retrieve(make_client, monkeypatch):
    monkeypatch.delenv("TRANSCDR_API_KEY", raising=False)
    rec = Recorder(json_response(200, STATS))
    stats = make_client(rec, api_key=None).stats.retrieve()
    assert (rec.requests[0].method, rec.requests[0].url.path) == ("GET", "/v1/stats")
    assert "Authorization" not in rec.requests[0].headers  # public endpoint
    assert stats["object"] == "stats"
    assert stats["totals"]["customers"] == 57
    assert stats["last_24h"]["jobs_completed"] == 42
    assert stats["daily"][0]["date"] == "2026-09-25"


def test_status_retrieve(make_client):
    body = {"object": "status", "status": "operational", "queue_depth": 3, "running_jobs": 2, "version": "1.4.0"}
    rec = Recorder(json_response(200, body))
    status = make_client(rec).status.retrieve()
    assert rec.requests[0].url.path == "/v1/status"
    assert status["version"] == "1.4.0"
