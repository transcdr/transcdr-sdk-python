# Transcdr Python SDK

The official Python client for the [Transcdr](https://transcdr.com) video-transcoding API:
AV1, H.264 and H.265 transcodes, MP4 renditions and CMAF/HLS ABR ladders.

- Sync (`Transcdr`) and asyncio (`AsyncTranscdr`) clients with the same surface
- Typed responses (`TypedDict`s in `transcdr.types`) — every object is a plain `dict`
- Cursor pagination with `auto_paging_iter()`
- Automatic retries with exponential backoff and jitter, made safe by idempotency keys
- One-call file uploads and job polling
- Storage connections (S3, R2, B2, MinIO, GCS, Azure, FTP/FTPS, SFTP, HTTP, WebDAV), messaging
  connections (SQS, SNS, webhooks), deliveries, and watch, hook and queue automations
- Event destinations on HTTPS, Amazon SNS and Amazon SQS, and signature verification for all three
- Constant bit rate output, several organizations per login, and the input report

Requires Python 3.9+. The only dependency is [`httpx`](https://www.python-httpx.org/).

The SDK is installed from this repository (it is not on PyPI yet):

```sh
pip install "transcdr @ git+https://github.com/transcdr/transcdr-sdk-python@v0.3.0"
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

### Constant bit rate

`quality.target = "cbr"` codes every rendition at a constant bit rate instead of to a quality
level, for players, networks and broadcast chains that need predictable bandwidth. Each rendition
takes its own `bitrate`, else `quality.bitrate`, else a default for its resolution and codec,
held within a buffer of `buffer_ms` (default 1000):

```python
preset = client.presets.create(
    name="Broadcast CBR",
    output={
        "mode": "hls",
        "codec": "h264",
        "quality": {"target": "cbr", "bitrate": "3M", "buffer_ms": 1500},
        "renditions": [
            {"width": 1920, "height": 1080, "bitrate": "6M"},
            {"width": 1280, "height": 720},  # at quality.bitrate
        ],
    },
)
job = client.jobs.create(input="ast_...", preset=preset["id"])
```

A `crf`, or a rate without `"cbr"`, is refused with an `InvalidRequestError`.

### Audio: MP3, audio-only, channels

`"mode": "audio"` writes the audio alone as one `.mp3` file (label `audio`, width and height 0),
billed per output minute at the SD rate; a `single` job whose input has no video becomes
audio-only by itself. `audio.mode = "mp3"` puts constant bit rate MP3 in a single MP4 or an
audio-only output (not HLS), stereo at most, at 32k, 40k, 48k, 56k, 64k, 80k, 96k, 112k, 128k,
160k, 192k, 224k, 256k or 320k (default 128k stereo, 64k mono).

`audio.channels` is `"source"` (the default), `"mono"`, `"stereo"`, `"5.1"` or `"7.1"`
(`transcdr.types.AudioChannels`); it downmixes and never upmixes. In HLS with surround audio,
`audio.stereo_fallback = True` adds a stereo rendition to the same audio group.

```python
# A podcast episode from a video recording.
job = client.jobs.create(
    input="ast_...",
    output={"mode": "audio", "audio": {"mode": "mp3", "bitrate": "128k", "channels": "stereo"}},
)

# Surround HLS with a stereo rendition beside it.
job = client.jobs.create(
    input="ast_...",
    output={"mode": "hls", "codec": "h264", "audio": {"channels": "5.1", "stereo_fallback": True}},
)
```

The `audio-mp3-podcast` and `audio-mp3-speech` system presets (category `audio`) are MP3 at 128k
stereo and 64k mono.

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

Every method has an async twin on `AsyncTranscdr`. The surface matches the TypeScript SDK 0.5.0.

| Attribute | Methods |
|---|---|
| `client.auth` | `register`, `login` (with `organization_id=`), `switch`, `logout`, `change_password`, `me` |
| `client.organization` | `retrieve`, `update`, `rotate_job_webhook_secret`; `.members`: `list`, `create`, `update`, `delete`, `leave` |
| `client.organizations` | `list`, `create` (the user's organizations; session tokens only) |
| `client.api_keys` | `list`, `retrieve` (404 once revoked), `create`, `delete` (`revoke`) |
| `client.uploads` | `create`, `complete`, `upload_file` |
| `client.assets` | `list`, `create` (import by URL), `retrieve`, `delete`, `download_url`, `content_url` |
| `client.jobs` | `create`, `list`, `retrieve`, `cancel`, `retry`, `delete`, `events`, `outputs`, `output_url`, `file_url`, `deliveries`, `deliver`, `wait` |
| `client.deliveries` | `retry` |
| `client.probe` | `create(input=..., wait=True)` |
| `client.presets` | `list(category=..., compatible_with=...)`, `create`, `retrieve`, `update` (PATCH: `output` merges), `replace` (PUT: the whole preset), `delete` |
| `client.webhooks` | `list`, `create` (HTTPS, SNS, SQS or a connection), `retrieve`, `update`, `delete`, `rotate_secret`, `test`, `check`, `check_saved`, `deliveries`, `redeliver`, `verify_signature`, `verify_sns_sqs_signature`, `construct_event` |
| `client.connections` | `list`, `create`, `retrieve`, `update`, `enable`, `disable`, `delete`, `test`, `check`, `check_saved`, `browse` |
| `client.automations` | `list`, `create`, `retrieve`, `update`, `delete`, `run`, `trigger`, `rotate_hook_token`, `items` |
| `client.events` | `list(type=...)`, `retrieve` |
| `client.usage` | `retrieve(from_=..., to=..., granularity=...)`, `inputs(from_=..., to=...)` |
| `client.billing` | `retrieve`, `checkout(plan= \| credit_cents=)`, `portal`, `update_settings`, `transactions`, `change_plan`; `.invoices`: `list` (monthly statements) |
| `client.plans` | `list` |
| `client.capabilities` | `retrieve` |
| `client.status` | `retrieve` |
| `client.stats` | `retrieve` (public platform statistics) |
| `client.announcements` | `list(unseen=, kind=, limit=)`, `mark_seen`, `mark_all_seen` |
| `client.changelog` | `list` (public) |
| `client.admin` | `overview`, `jobs`, `organizations`, `update_organization`, `grant_credit`; `.announcements`: `list`, `create`, `update`, `delete`; `.incidents`: `detectors`, `list`, `create`, `retrieve`, `preview`, `apply` (platform operators only) |

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
| `QuotaError` | 402: `insufficient_credit`, `cost_limit_exceeded` or `spend_limit_reached` |
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

## Credit and spending

Transcoding is paid from prepaid credit, per output minute: $0.005 SD, $0.010 HD and $0.025 UHD,
whatever the codec. A job the account cannot pay for is refused before it starts with a
`QuotaError` (402).

```python
billing = client.billing.retrieve()
print(billing["account"]["available_usd"], billing["account"]["this_month"]["spent_usd"])

# Cap a single job.
client.jobs.create(input="ast_...", preset="hls-av1-abr", max_cost_cents=200)

# Buy $50 of credit, or subscribe: send the customer to `url`.
checkout = client.billing.checkout(credit_cents=5000)

# A monthly limit and auto-recharge (needs a card saved by an earlier purchase).
client.billing.update_settings(
    monthly_limit_cents=50_000,
    auto_recharge={"enabled": True, "threshold_cents": 1000, "amount_cents": 5000, "monthly_cap_cents": 20_000},
)

for entry in client.billing.transactions(limit=20):
    print(entry["created_at"], entry["kind"], entry["amount_usd"])
```

`update_settings(monthly_limit_cents=None)` removes the monthly limit; leaving an argument out
leaves that setting as it is. The same goes for `auto_recharge={"monthly_cap_cents": None}`.

### The input report

`usage.inputs()` buckets the inputs a date range's jobs read by duration, size and kind
(`container/codec`), for a duration × size chart:

```python
report = client.usage.inputs(from_="2026-09-01", to="2026-09-30")
for kind in report["kinds"]:
    print(kind["kind"], kind["files"], kind["size_bytes"], kind["input_minutes"])
for point in report["points"]:
    print(point["kind"], point["mean_duration_seconds"], point["mean_size_bytes"], point["files"])
```

## Retries and idempotency

Requests are retried up to `max_retries` times (default 2) on connection errors, 408, 429 and
5xx, with exponential backoff and jitter (a short `Retry-After` is honoured). Only requests that
are safe to replay are retried: `GET`, `PUT`, `DELETE`, and `POST`s that carry an
`Idempotency-Key`. Every create (`jobs`, `probe`, `uploads`, `assets`, `presets`, `webhooks`,
`connections`, `automations`, `api_keys`, `organization.members`, `organizations`) sends a UUID
key, so a retry never creates a duplicate: the API replays the first response (with
`Idempotent-Replayed: true`). Keys last 24 hours per organization. Pass `idempotency_key=` to
control it yourself (e.g. to make your own job submission idempotent across process restarts).
The same key with a different body raises a 409 `idempotency_key_reused`; only a successful
create is remembered, so after an error the key can be used again.

```python
client = Transcdr(timeout=30, max_retries=4)
client.with_options(max_retries=0).jobs.retrieve("job_...")
```

## Preset categories and compatibility

Every preset has a `category` (`web`, `mobile`, `streaming`, `tv`, `social`, `audio`, `archive`),
the group it is shown in, and `compatibility`: the platforms its output plays on (`web`, `ios`,
`android`, `smart_tv`, `legacy`, `editing`), with `compatibility_notes` giving each one's minimum
versions and conditions, such as audio that needs an AAC source. Both are derived from the
preset's `output`; the type aliases are `transcdr.types.PresetCategory` and
`transcdr.types.Platform`. More values may be added, so treat unknown ones gracefully.

```python
# Presets in either category that play on both iOS and Android.
page = client.presets.list(category=["web", "mobile"], compatible_with=["ios", "android"])
for preset in page.data:
    print(preset["slug"], preset["compatibility"], preset["compatibility_notes"].get("ios"))

# Your own preset may state its own; None derives them from its output again.
client.presets.update("pre_...", category="tv", compatibility=["smart_tv", "legacy"])
client.presets.update("pre_...", category=None, compatibility=None)
```

## Updating: left out, or None

`update` methods send `PATCH`: an argument left out keeps its value, and `None` clears it. That
covers an automation's `destination`, `preset`, `output`, `metadata`, `webhook_url` and
`trigger_connection_id`; a webhook's `description` (and `endpoint` / `message_group_id` inside
`aws`); a connection's `config` fields and storage `secrets`; a preset's `description` and
`metadata` (and `category`, `compatibility` and `compatibility_notes`, which `None` derives
again); and the organization's `billing_email`. (On `create`, `None` still means "not
given".)

```python
client.automations.update("aut_...", destination=None, webhook_url=None)
client.presets.replace("pre_...", name="Web 1080p", output={"codec": "av1"})  # PUT: the whole preset
```

Connections and webhooks never return their secrets. `secrets` lists the ones that are set, each
with a `fingerprint` (`hmac-sha256:<12 hex>`) that changes when the secret does: compare it with
an earlier read to notice a change made elsewhere.

`client.auth.me()` returns a `user` for API keys too (the user who created the key); use
`transcdr.is_session(me)` to tell a session (`api_key.prefix` starts `tds_`) from an API key.

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

### Amazon SNS and SQS destinations

An event destination can also publish to an SNS topic or send to an SQS queue, or go through a
messaging connection that holds the target and keys:

```python
client.webhooks.create(url="https://example.com/hooks/transcdr", events=["job.completed", "job.failed"])
client.webhooks.create(
    topic_arn="arn:aws:sns:us-east-1:123456789012:transcdr-events",
    aws={"access_key_id": "AKIA...", "secret_access_key": "..."},
)
client.webhooks.create(
    queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/transcdr-events",
    aws={"access_key_id": "AKIA...", "secret_access_key": "..."},
)
client.webhooks.create(connection_id="con_...")                  # an sqs, sns or webhook connection
client.webhooks.check(url="https://example.com/hooks/transcdr")  # try it without saving
```

SNS and SQS deliveries carry the signature in the `transcdr-signature` message attribute, over
`"<t>.<message>"`. `verify_sns_sqs_signature` takes the attribute map in any AWS shape: boto3 and
`ReceiveMessage` (`StringValue`), Lambda SQS events (`stringValue`) and SNS JSON (`Value`):

```python
from transcdr.webhooks import verify_sns_sqs_signature

def handler(event, context):                                  # an SQS-triggered Lambda
    for record in event["Records"]:
        if not verify_sns_sqs_signature(record["body"], record["messageAttributes"], SECRET):
            raise ValueError("bad signature")
```

With raw message delivery off, an SNS to SQS subscription wraps the notification: parse the body
and pass its `Message` and `MessageAttributes` instead.

## Integrations: connections, deliveries and automations

Available on the Starter plan and above. A **storage connection** is your own storage: jobs can
read inputs from it and deliver outputs to it. A **messaging connection** (`sqs`, `sns`,
`webhook`) receives events, and an `sqs` connection can trigger queue automations. Connections
are tested when they are saved and on every update; the outcome is in `status` and `last_error`.
Secret values are write-only (the API returns only their names in `secrets_set`). On `update`,
`config` merges (a `None` value clears that field), an omitted secret is kept, and `""` or `None` clears it.

A connection that keeps failing is turned off (`enabled: False`, with `disabled_reason`), and
anything using it is refused until `client.connections.enable(id)` turns it back on.

### Connection examples by provider

**Amazon S3**

```python
s3 = client.connections.create(
    name="AWS ingest",
    kind="s3",
    config={"bucket": "my-videos", "region": "us-east-1", "root": "transcdr/"},
    secrets={"access_key_id": "AKIA...", "secret_access_key": "..."},  # + optional "session_token"
)
```

**Cloudflare R2**

```python
r2 = client.connections.create(
    name="R2 outputs",
    kind="s3",
    config={
        "bucket": "outputs",
        "region": "auto",
        "endpoint": "https://<account_id>.r2.cloudflarestorage.com",
    },
    secrets={"access_key_id": "...", "secret_access_key": "..."},
)
```

**Backblaze B2** (S3-compatible API)

```python
b2 = client.connections.create(
    name="B2 archive",
    kind="s3",
    config={
        "bucket": "archive",
        "region": "us-west-004",
        "endpoint": "https://s3.us-west-004.backblazeb2.com",
    },
    secrets={"access_key_id": "<keyID>", "secret_access_key": "<applicationKey>"},
)
```

**MinIO** (and other self-hosted S3; usually needs path-style addressing)

```python
minio = client.connections.create(
    name="MinIO",
    kind="s3",
    config={
        "bucket": "media",
        "region": "us-east-1",
        "endpoint": "https://minio.example.com",
        "path_style": True,
    },
    secrets={"access_key_id": "...", "secret_access_key": "..."},
)
```

**Google Cloud Storage**

```python
gcs = client.connections.create(
    name="GCS",
    kind="gcs",
    config={"bucket": "my-gcs-bucket", "root": "videos/"},
    secrets={"service_account_json": open("service-account.json").read()},
)
```

**Azure Blob Storage** (`bucket` is the container name)

```python
azure = client.connections.create(
    name="Azure",
    kind="azure_blob",
    config={"account": "mystorageacct", "bucket": "videos"},
    secrets={"account_key": "..."},  # or {"sas_token": "sv=..."}
)
```

**FTP / FTPS**

```python
ftp = client.connections.create(
    name="Broadcaster FTPS",
    kind="ftps",  # or "ftp"
    config={"host": "ftp.example.com", "port": 21, "username": "uploader", "root": "/drop", "passive": True},
    secrets={"password": "..."},
)
```

**SFTP**

```python
sftp = client.connections.create(
    name="SFTP",
    kind="sftp",
    config={
        "host": "sftp.example.com",
        "port": 22,
        "username": "media",
        "root": "/srv/media",
        "host_key_fingerprint": "SHA256:...",
    },
    secrets={"private_key": open("id_ed25519").read()},  # or {"password": "..."}; + "private_key_passphrase"
)
```

**HTTP** (read-only: a source, never a destination)

```python
http = client.connections.create(
    name="Origin",
    kind="http",
    config={"endpoint": "https://media.example.com/", "username": "reader"},
    secrets={"password": "..."},  # basic auth; or {"bearer_token": "..."}
)
```

**WebDAV**

```python
dav = client.connections.create(
    name="Nextcloud",
    kind="webdav",
    config={"endpoint": "https://cloud.example.com/remote.php/dav/files/me/", "username": "me", "root": "Videos/"},
    secrets={"password": "<app password>"},  # or {"bearer_token": "..."}
)
```

Check settings before saving them, or a saved connection, step by step, with the roles it can
serve and provider-specific setup such as a least-privilege IAM policy:

```python
report = client.connections.check(kind="s3", config={"bucket": "my-videos", "region": "us-east-1"},
                                  secrets={"access_key_id": "AKIA...", "secret_access_key": "..."})
for step in report["steps"]:
    print(step["id"], step["status"], step.get("detail"), step.get("hint"))
print(report["roles"], report["setup"]["iam_policy"])
client.connections.check_saved(s3["id"])
```

Test or explore a connection:

```python
result = client.connections.test(s3["id"])          # {"ok": ..., "error": ..., "connection": ...}
for obj in client.connections.browse(s3["id"], prefix="incoming/", recursive=True).auto_paging_iter():
    print(obj["path"], obj["size"], obj["last_modified"])
```

### Jobs that read from and deliver to connections

```python
job = client.jobs.create(
    input={"type": "connection", "connection_id": s3["id"], "path": "incoming/talk.mov"},
    preset="hls-av1-abr",
    destination={"connection_id": r2["id"], "prefix": "out/{job_id}/"},  # the whole HLS tree is delivered
)

client.jobs.deliveries(job["id"]).data                                 # delivery status per destination
client.jobs.deliver(job["id"], connection_id=b2["id"], prefix="archive/{job_id}/")  # deliver (again)
client.deliveries.retry("dlv_...")                                     # retry a failed delivery now
```

Object stores and HTTP inputs are read directly through a signed URL; FTP, SFTP and
WebDAV inputs are copied in first. Deliveries retry on the webhook schedule and emit
`job.delivered` / `job.delivery_failed` events.

### Automations

"When a file lands in a connection, transcode it like this, deliver it there." Each object
version is processed exactly once.

```python
automation = client.automations.create(
    name="Ingest -> HLS",
    trigger="watch",                      # poll the source; or "hook" for push notifications
    source={"connection_id": s3["id"], "prefix": "incoming/", "pattern": "**/*.{mp4,mov}"},
    poll_interval_seconds=300,            # list the source every 5 minutes
    settle_seconds=60,                    # only take files unchanged for a minute
    preset="hls-av1-abr",
    output={"quality": {"target": "high"}},
    destination={"connection_id": r2["id"], "prefix": "{automation}/{date}/{stem}/"},
    after_success="delete",               # remove the source file once delivered ("keep" is the default)
    metadata={"pipeline": "ingest"},
)

client.automations.run(automation["id"])                              # poll now -> {"jobs_created": n}
client.automations.trigger(automation["id"], path="incoming/late.mov")  # -> {"jobs_created", "job_ids"}
for item in client.automations.items(automation["id"]).auto_paging_iter():
    print(item["path"], item["status"], item["job_id"], item["error"])
client.automations.update(automation["id"], enabled=False)
```

Destination prefix templates: `{job_id}`, `{name}`, `{stem}`, `{ext}`, `{dir}`, `{date}`,
`{automation}`, `{org}`.

With `trigger="hook"`, point bucket notifications (S3/R2/MinIO, directly or via SNS, or GCS) or
your own system at the automation's `hook_url`, e.g. `POST {"path": "incoming/a.mp4"}` or
`{"paths": [...]}`. `client.automations.rotate_hook_token(id)` issues a new `hook_url`.

With `trigger="queue"`, the automation consumes an `sqs` connection: S3 notifications sent to the
queue directly or through an SNS topic, EventBridge `Object Created` events, `{"path": ...}`
messages and job requests. No public endpoint is involved.

```python
queue = client.connections.create(
    name="Upload events",
    kind="sqs",
    config={"queue_url": "https://sqs.us-east-1.amazonaws.com/123456789012/uploads"},
    secrets={"access_key_id": "AKIA...", "secret_access_key": "..."},
)
automation = client.automations.create(
    name="Uploads",
    trigger="queue",
    trigger_connection_id=queue["id"],
    source={"connection_id": s3["id"], "prefix": "incoming/"},
    preset="hls-h264-abr",
)
client.automations.run(automation["id"])   # read one batch now -> messages_received, messages_deleted, jobs_created
```

To clear a value with `update`, pass `None`: `preset=None`, `webhook_url=None`,
`trigger_connection_id=None`, `destination=None`, `output=None` or `metadata=None`.

## Organizations

One login can belong to several organizations. With a session token:

```python
session = client.auth.login(email="person@example.com", password="...", organization_id="org_...")
client.api_key = session["token"]
for membership in session["organizations"]:
    print(membership["organization"]["name"], membership["role"])

switched = client.auth.switch("org_other")   # revokes the current token
client.api_key = switched["token"]
new = client.organizations.create(name="Side project")   # a token in the new organization
client.organization.members.create(email="teammate@example.com", role="admin")  # an existing user
```

## Test mode

Keys starting with `tdk_test_` run in test mode: jobs are never really processed; they complete with
synthetic outputs after a few seconds, are free, and carry `"livemode": false`. Use them in CI and
local development; `client.livemode` tells you which kind of key a client holds.

## Configuration

| Argument | Default |
|---|---|
| `api_key` | `$TRANSCDR_API_KEY` (a `tdk_live_`/`tdk_test_` key or a `tds_` session token) |
| `base_url` | `$TRANSCDR_BASE_URL`, else `https://api.transcdr.com` (`http://localhost:8080` in development) |
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

## License

MIT
