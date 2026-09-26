# Transcdr Python SDK

The official Python client for the [Transcdr](https://transcdr.io) video-transcoding API:
AV1, H.264 and H.265 transcodes, MP4 renditions and CMAF/HLS ABR ladders.

- Sync (`Transcdr`) and asyncio (`AsyncTranscdr`) clients with the same surface
- Typed responses (`TypedDict`s in `transcdr.types`) — every object is a plain `dict`
- Cursor pagination with `auto_paging_iter()`
- Automatic retries with exponential backoff and jitter, made safe by idempotency keys
- One-call file uploads and job polling
- Webhook signature verification

Requires Python 3.9+. The only dependency is [`httpx`](https://www.python-httpx.org/).

```sh
pip install transcdr
```

## Quickstart

Upload a local file, transcode it to an AV1 HLS ladder, wait for it, and get a download URL:

```python
from transcdr import Transcdr

client = Transcdr(api_key="tdk_live_...")  # or set TRANSCDR_API_KEY

# 1. Upload: creates an upload session, streams the bytes to storage, completes it.
asset = client.uploads.upload_file("keynote.mov")

# 2. Transcode with a system preset. `input` may be a dict, an `ast_` id or a URL.
job = client.jobs.create(
    input={"type": "asset", "asset_id": asset["id"]},
    preset="hls-av1-abr",
    metadata={"customer": "42"},
)

# 3. Wait for a terminal status (completed / failed / canceled).
job = client.jobs.wait(
    job["id"],
    poll_interval=2,
    timeout=3600,
    on_progress=lambda j: print(j["status"], j.get("progress", {}).get("percent")),
)

if job["status"] != "completed":
    raise SystemExit(f"job {job['status']}: {job.get('error')}")

# 4. Play or download.
print("player URL:", job["playback_url"])            # signed, expires in 6 h, no auth header needed
for output in job["outputs"]:
    signed = client.jobs.output_url(job["id"], output["label"])
    print(output["label"], signed["url"], "expires", signed["expires_at"])
```

For single-file MP4 output, customise the spec — `output` fields override the preset's:

```python
job = client.jobs.create(
    input="https://example.com/in.mp4",
    preset="web-av1-1080p",
    output={"quality": {"target": "high"}, "trim": {"start": 2.0, "end": 7.0}},
)
```

### Async

```python
import asyncio
from transcdr import AsyncTranscdr

async def main() -> None:
    async with AsyncTranscdr() as client:
        asset = await client.uploads.upload_file("keynote.mov")
        job = await client.jobs.create(input=asset["id"], preset="hls-av1-abr")
        job = await client.jobs.wait(job["id"])
        async for event in (await client.jobs.events(job["id"])).auto_paging_iter():
            print(event["type"], event["message"])

asyncio.run(main())
```

## Resources

| Attribute | Methods |
|---|---|
| `client.auth` | `register`, `login`, `logout`, `change_password`, `me` |
| `client.organization` | `retrieve`, `update`, `rotate_job_webhook_secret`; `.members`: `list`, `create`, `update`, `delete` |
| `client.api_keys` | `list`, `create`, `delete` (`revoke`) |
| `client.uploads` | `create`, `complete`, `upload_file` |
| `client.assets` | `list`, `create` (import by URL), `retrieve`, `delete`, `download_url` |
| `client.jobs` | `create`, `list`, `retrieve`, `cancel`, `retry`, `delete`, `events`, `outputs`, `output_url`, `file_url`, `wait` |
| `client.probe` | `create(input=..., wait=True)` |
| `client.presets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `client.webhooks` | `list`, `create`, `retrieve`, `update`, `delete`, `rotate_secret`, `test`, `deliveries`, `redeliver`, `verify_signature`, `construct_event` |
| `client.events` | `list(type=...)`, `retrieve` |
| `client.usage` | `retrieve(from_=..., to=..., granularity=...)` |
| `client.billing` | `retrieve`, `change_plan`; `.invoices`: `list` |
| `client.plans` | `list` |
| `client.capabilities` | `retrieve` |
| `client.status` | `retrieve` |

Anything not wrapped yet: `client.request("GET", "/v1/openapi.json")`.

## Pagination

List methods return a page with `.data`, `.has_more` and `.next_cursor`:

```python
page = client.jobs.list(status="completed", limit=50)
print(len(page.data), page.has_more, page.next_cursor)

for job in page.auto_paging_iter():    # fetches further pages lazily
    print(job["id"])

client.jobs.list(metadata={"customer": "42"})   # → ?metadata[customer]=42
```

## Errors

Every error derives from `transcdr.TranscdrError` and carries `.status`, `.type`, `.code`,
`.param`, `.details` and `.request_id`:

| Exception | When |
|---|---|
| `AuthenticationError` | 401 |
| `PermissionDeniedError` | 403, e.g. code `insufficient_scope` |
| `QuotaError` | 402 |
| `InvalidRequestError` | 400 / 409 / 422 (`NotFoundError` for 404) |
| `RateLimitError` | 429 (`.retry_after` seconds when known) |
| `APIError` | 5xx |
| `APIConnectionError` | network failure (`APITimeoutError` for timeouts) |
| `WaitTimeoutError` | `jobs.wait(timeout=...)` elapsed |
| `SignatureVerificationError` | `construct_event` rejected a webhook |

```python
import transcdr

try:
    client.jobs.create(input="https://example.com/in.mp4", output={"renditions": []})
except transcdr.InvalidRequestError as err:
    print(err.code, err.param, err.details, err.request_id)
```

## Retries and idempotency

Requests are retried up to `max_retries` times (default 2) on connection errors, 408, 429 and
5xx, with exponential backoff and jitter (a short `Retry-After` is honoured). Only requests that
are safe to replay are retried: `GET`, `PUT`, `DELETE`, and `POST`s that carry an
`Idempotency-Key`. `jobs.create` and `uploads.create` generate a UUID key automatically, so a
retry never creates a duplicate job; pass `idempotency_key=` to control it yourself (e.g. to
make your own job submission idempotent across process restarts).

```python
client = Transcdr(timeout=30, max_retries=4)
client.with_options(max_retries=0).jobs.retrieve("job_...")
```

## Webhooks

Each delivery carries `Transcdr-Signature: t=<unix>,v1=<hex hmac_sha256(secret, "<t>.<raw body>")>`.
Verify it against the **raw** request body with the endpoint's `whsec_…` secret (returned on
`webhooks.create` / `rotate_secret`; per-job `webhook_url` deliveries use the organization's
`job_webhook_secret`). Timestamps older than 5 minutes are rejected.

```python
from transcdr.webhooks import construct_event, verify_signature

verify_signature(raw_body, header, secret)            # -> bool
event = construct_event(raw_body, header, secret)     # -> Event, or raises SignatureVerificationError
```

Flask:

```python
import os
from flask import Flask, request
from transcdr import SignatureVerificationError
from transcdr.webhooks import construct_event

app = Flask(__name__)
SECRET = os.environ["TRANSCDR_WEBHOOK_SECRET"]

@app.post("/hooks/transcdr")
def transcdr_webhook():
    try:
        event = construct_event(
            request.get_data(), request.headers.get("Transcdr-Signature"), SECRET
        )
    except SignatureVerificationError:
        return "bad signature", 400
    if event["type"] == "job.completed":
        job = event["data"]["object"]
        print("done:", job["id"], job["playback_url"])
    return "", 204
```

FastAPI:

```python
import os
from fastapi import FastAPI, Header, HTTPException, Request
from transcdr import SignatureVerificationError
from transcdr.webhooks import construct_event

app = FastAPI()
SECRET = os.environ["TRANSCDR_WEBHOOK_SECRET"]

@app.post("/hooks/transcdr", status_code=204)
async def transcdr_webhook(request: Request, transcdr_signature: str = Header(None)):
    try:
        event = construct_event(await request.body(), transcdr_signature, SECRET)
    except SignatureVerificationError:
        raise HTTPException(status_code=400, detail="bad signature")
    if event["type"] == "job.failed":
        job = event["data"]["object"]
        print("failed:", job["id"], job["error"])
```

Respond with a 2xx quickly; failed deliveries are retried after 1 m, 5 m, 30 m, 2 h, 6 h and 12 h.
Use `transcdr.webhooks.sign_payload(body, secret)` to build valid headers in your own tests.

## Test mode

Keys starting with `tdk_test_` run in test mode: jobs are never really processed; they complete with
synthetic outputs after a few seconds, are free, and carry `"livemode": false`. Use them in CI and
local development; `client.livemode` tells you which kind of key a client holds.

## Configuration

| Argument | Default |
|---|---|
| `api_key` | `$TRANSCDR_API_KEY` (a `tdk_live_`/`tdk_test_` key or a `tds_` session token) |
| `base_url` | `$TRANSCDR_BASE_URL`, else `https://api.transcdr.io` (`http://localhost:8080` in development) |
| `timeout` | 60 s (float or `httpx.Timeout`) |
| `max_retries` | 2 |
| `default_headers` | extra headers on every request |
| `http_client` | your own `httpx.Client` / `httpx.AsyncClient` (proxies, transports, …) |

Clients hold a connection pool: reuse one per process, and `close()` it (or use `with`) when done.

## Development

```sh
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # Windows: .venv\Scripts\pip
.venv/bin/pytest
```
