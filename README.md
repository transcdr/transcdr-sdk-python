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
- Output spec v2: typed, sectioned specs with no defaults, checked before they are sent
- Constant bit rate output, several organizations per login, and the input report

Requires Python 3.9+. The only dependency is [`httpx`](https://www.python-httpx.org/).

The SDK is installed from this repository (it is not on PyPI yet):

```sh
pip install "transcdr @ git+https://github.com/transcdr/transcdr-sdk-python@v1.0.0"
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

With a preset, `output` gives only the fields to change; without one, it is a whole spec (see
[Output specs](#output-specs-v2)):

```python
job = client.jobs.create(
    input="https://example.com/in.mp4",
    preset="web-av1-1080p",
    output={"video": {"quality": "high"}, "trim": {"start": 2.0, "end": 7.0}},
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

## Output specs (v2)

A job's `output` says what it produces, declared in sections:

| Section | Describes | For kind |
|---|---|---|
| `kind` | What is produced: `video`, `audio` or `image` | all |
| `container` | The file or package: `format` (`mp4`, `hls`; `mp3`, `flac`, `m4a`), and `segment_seconds` for `hls` | video, audio |
| `video` | The video track | video |
| `audio` | The audio track | video, audio |
| `image` | Still images | image |
| `renditions` | The sizes produced: exactly one of `sizes`, `ladder` (video) or `source_size` | video, image |
| `subtitles` | Which subtitle tracks are carried: `tracks` (`all`, `none`) or `languages` | video |
| `trim` | Which part of the source is used | video |
| `privacy` | Which identifying metadata survives: `preset`, or all four of `location`, `capture_time`, `device`, `descriptive` | all |

**Nothing has a default.** A spec sent without a preset states every field its kind, container,
codec and handling need, and the SDK fills nothing in. A value that follows the source is a value
you write:

| Value | Resolves to |
|---|---|
| `video.frame_rate.max: "source"` | the source's frame rate, not capped |
| `video.bit_depth: "from_color"` | 8-bit for `sdr`, 10-bit for `hdr10` / `hlg`, the source's for `passthrough` |
| `video.cbr.bitrate: "standard"` | a rate for each size by codec, short side and frame rate (H.264 at 30 fps: about 5M at 1080p, 3M at 720p, 1.2M at 480p, 0.8M at 360p; H.265 about 0.65x, AV1 about 0.5x) |
| `video.gop: "segment"` | HLS: one keyframe at the start of each segment |
| `audio.bitrate: "standard"` | AAC 64k mono, 128k stereo, 384k 5.1, 512k 7.1; Opus 96k stereo, 320k 5.1, 416k 7.1; MP3 64k mono, 128k stereo |
| `audio.channels: "source"` | the source's layout (MP3 folds a wider one to stereo) |
| `audio.bit_depth: "source"` | 16-bit for a 16-bit or lossy source, 24-bit for a deeper one |
| `audio.he_aac: "auto"` | an HE-AAC source passes through where only a codec change is asked; its AAC-LC core is decoded where the job needs PCM |
| `label: "by_size"` | video: `<short side>p` of the size it comes out at; image: `<width>x<height>` |
| `trim.end: "source"` | the end of the source |
| `image.frames: "poster"` | an image input as it is; a video's frame 10% of the way in |
| `subtitles.tracks: "all"` | every subtitle track of the source |

The types are in `transcdr.types`: `OutputSpec` is `VideoOutput | AudioOutput | ImageOutput`,
each a `TypedDict` whose always-required keys are required, so a type checker flags a missing
section. Choices of which exactly one is given are unions (`VideoQuality | VideoCrf | VideoCbr`,
`RenditionSizes | RenditionLadder | RenditionSourceSize`, `SubtitleTracks | SubtitleLanguages`,
`PrivacyPreset | PrivacyFields`, `AudioTrack | AudioDrop`). Fields needed only under a condition
(an HLS container's `segment_seconds`, a lossy codec's `audio.bitrate`, `flac`'s
`flac_compression`, WebP's `image.lossless`) are optional keys, checked at run time.

### Checked before it is sent

`transcdr.validate_output(spec)` checks a whole spec against the same table the API uses and
returns every problem at once, in the API's words: fields that are missing (by full path, with
the condition that needs them), fields that don't apply, and exclusive groups with no choice or
more than one. `jobs.create`, `presets.create`, `presets.replace` and `automations.create` run it
on a whole spec sent without a preset, and raise `InvalidRequestError` (code
`validation_failed`) with every failure in `err.errors`, without sending the request. A job with
neither a preset nor an `output` is refused the same way. The API makes the same check (and
checks values against each other, such as HDR with 8-bit or MP3 in HLS) and answers a 422 with
the same `errors` list.

```python
import transcdr

spec = {"kind": "audio", "container": {"format": "mp3"}, "privacy": {"preset": "strip_all"},
        "audio": {"handling": "encode", "codec": "mp3", "channels": "mono", "he_aac": "auto"}}
transcdr.validate_output(spec)
# [{'param': 'output.audio.bitrate',
#   'message': 'output.audio.bitrate is required when kind is video or audio and audio.handling
#               is auto or encode and audio.codec is opus, mp3 or aac.'}]
```

### Examples

An ABR HLS ladder of explicit sizes, H.264 at a constant bit rate:

```python
job = client.jobs.create(
    input="ast_...",
    output={
        "kind": "video",
        "container": {"format": "hls", "segment_seconds": 6},
        "video": {
            "codec": "h264",
            "cbr": {"bitrate": "standard", "buffer_ms": 1000},  # exactly one of cbr | quality | crf
            "bit_depth": "8bit",
            "color": "sdr",
            "frame_rate": {"max": "source"},
            "gop": "segment",
            "filters": [],
        },
        "audio": {"handling": "encode", "codec": "aac", "bitrate": "standard", "channels": "source",
                  "he_aac": "auto", "stereo_fallback": False},
        "renditions": {"sizes": [
            {"label": "by_size", "width": 1920, "height": 1080, "fit": "contain", "orientation": "auto",
             "upscale": False, "video": {"cbr": {"bitrate": "5M"}}},
            {"label": "by_size", "width": 1280, "height": 720, "fit": "contain", "orientation": "auto",
             "upscale": False, "video": {"cbr": {"bitrate": "3M"}}},
        ]},
        "subtitles": {"tracks": "all"},
        "trim": {"start": 0, "end": "source"},
        "privacy": {"preset": "strip_all"},
    },
)
# An automatic ladder instead:
#   "renditions": {"ladder": {"max_short_side": 1080, "fit": "contain", "upscale": False}}
```

A single vertical MP4 for social apps:

```python
output = {
    "kind": "video",
    "container": {"format": "mp4"},
    "video": {"codec": "h264", "quality": "high", "bit_depth": "from_color", "color": "sdr",
              "frame_rate": {"max": 30}, "gop": {"seconds": 2}, "filters": []},
    "audio": {"handling": "encode", "codec": "aac", "bitrate": "standard", "channels": "source",
              "he_aac": "auto"},
    "renditions": {"sizes": [{"label": "by_size", "width": 1080, "height": 1920, "fit": "cover",
                              "orientation": "fixed", "upscale": False}]},
    "subtitles": {"tracks": "all"},
    "trim": {"start": 0, "end": "source"},
    "privacy": {"preset": "strip_all"},
}
```

An audio-only MP3:

```python
output = {
    "kind": "audio",
    "container": {"format": "mp3"},
    "audio": {"handling": "encode", "codec": "mp3", "bitrate": "64k", "channels": "mono", "he_aac": "auto"},
    "privacy": {"preset": "strip_all"},
}
```

Twelve evenly spaced JPEG stills of a video:

```python
output = {
    "kind": "image",
    "image": {"formats": ["jpeg"], "quality": {"jpeg": 80}, "color_profile": "srgb", "frames": {"count": 12}},
    "renditions": {"sizes": [{"label": "sheet", "width": 320, "height": 320, "fit": "contain",
                              "orientation": "auto", "upscale": False}]},
    "privacy": {"preset": "strip_all"},
}
```

### Presets, versions and overrides

A preset is a whole spec, and it is versioned: editing a preset's output adds a version, and a
version never changes. Name one by slug or id for its latest version, or `slug@N` to pin version
N. With a preset, `output` gives only what to change: objects merge key by key, scalars and
lists (`sizes`, `formats`, `filters`, …) replace, one choice of a group (`crf` over `quality`,
`ladder` over `sizes`, `languages` over `tracks`) replaces the others, `None` removes a field, and
`kind` cannot change. The result must be complete; the SDK leaves checking it to the API, which
does not know it until it merges.

```python
job = client.jobs.create(
    input="ast_...",
    preset="social-vertical-1080x1920@1",
    output={"video": {"frame_rate": {"max": 24}}},
)
job["preset"]   # {"id": "social-vertical-1080x1920", "version": 1, "overrides": {"video": {...}}}
job["output"]   # the resolved, complete spec: what runs, and what a rerun uses

# An HLS preset turned into an MP4: segment_seconds no longer applies, so remove it.
client.jobs.create(input="ast_...", preset="hls-h264-abr",
                   output={"container": {"format": "mp4", "segment_seconds": None},
                           "video": {"gop": {"seconds": 2}}, "audio": {"stereo_fallback": None}})

for version in client.presets.versions("web-avif").auto_paging_iter():
    print(version["version"], version["output"]["image"]["formats"])
client.presets.get_version("web-avif", 1)          # GET /v1/presets/web-avif@1
client.presets.update("pre_...", output={"video": {"crf": 23}})   # a new version
```

A job's `preset` is `{"id", "version", "overrides"}`, or `None` when it was given a whole spec.
Jobs, presets and automations always return the resolved spec, with `privacy` written out as all
four categories. An automation stores `preset` and its `output` overrides, and shows what they
resolve to now as `resolved_output`.

### Audio

- `handling: "auto"` keeps compatible audio as it is (AAC, Opus, AC-3, E-AC-3, DTS; MP3 too into
  an MP4) and makes the rest `codec`; `"encode"` makes `codec`, copying a source already in it when
  nothing else changes; `"drop"` has no audio track (and no other audio fields).
- `aac` is AAC-LC, which every browser, iPhone, Android device and TV plays: choose it for reach.
  8k to 288k per main channel.
- `mp3` is constant bit rate at 32k, 40k, 48k, 56k, 64k, 80k, 96k, 112k, 128k, 160k, 192k, 224k,
  256k or 320k, stereo at most; for an MP4 or an `.mp3`, not HLS.
- `flac` and `alac` are lossless and take no bitrate; they need `bit_depth` (`source`, `16`,
  `24`), and `flac` needs `flac_compression` (`fast`, `balanced`, `best`).
- `channels` downmixes (ITU-R BS.775) and never upmixes. In HLS, `stereo_fallback: True` adds a
  stereo downmix beside surround audio.
- `he_aac`: HE-AAC decodes only as its AAC-LC core (half the sample rate, less bandwidth).
  `passthrough` never decodes it, failing a job that would need it; `core` decodes its core
  whenever another codec or a change is asked.

Kind `audio` writes one file, `audio.mp3`, `audio.flac` or `audio.m4a` (label `audio`, width and
height 0), billed per output minute at the SD rate. An `.mp3` holds MP3 only, a `.flac` FLAC only,
an `.m4a` any codec.

### Images

Kind `image` makes stills of an image input (JPEG, PNG, WebP, AVIF, GIF, TIFF, BMP, HEIC) or of a
video. Every size is made in every format of `image.formats` (`avif`, `webp`, `jpeg`, `png`).
`image.quality` has one entry for each lossy format made (`{"avif": 60, "jpeg": 82}`); `lossless`
is required with `webp`. Image sizes are 16 to 8192 on a side, odd sizes allowed. Each output
carries its `format`, its `rendition`, and for a video's stills its `frame` and `at_seconds`.
Images are billed per output image by pixel count: `billing.billable_images`, `billing.tier`
(`up_to_1mp`, `up_to_4mp`, `over_4mp`).

System presets include `web-avif`, `web-webp`, `thumbnail-jpeg`, `png-lossless`, `video-poster`,
`contact-sheet` (images), `audio-mp3-podcast`, `audio-mp3-speech`, `audio-aac-m4a`,
`audio-alac-m4a`, `audio-flac` (audio) and the video presets such as `hls-av1-abr`,
`hls-h264-abr`, `hls-h264-cbr`, `web-av1-1080p` and `social-vertical-1080x1920`.

### Capabilities

`client.capabilities.retrieve()["output"]` describes the spec as data: `fields` (each `path`,
whether it is `required`, the conditions `when` it applies, its `shape` and exclusive `group`),
`groups`, `containers` (and the audio codecs each holds), `audio_codecs`, `follow_values` and
`compatibility`. `transcdr.validate_output` checks the same table.

## Migrating from v1

1.0 speaks output spec v2 only: requests are sent, and responses read, in the v2 shape. 0.x
releases keep working unchanged: the API reads a v1 `output` (one without `kind`) with v1's
defaults, and answers their requests in v1 through its compatibility mode (the
`Transcdr-Output-Spec: v1` header, or `?output_spec=v1` on a `GET`). That mode is deprecated from
the start: its responses carry `Deprecation: true` and a `Sunset` date, and it is removed after
**31 March 2027**. Move to 1.0 before then.

What changes in your code:

- Every spec sent without a preset is whole: add the fields v1 defaulted (the right-hand column
  below), or start from a preset and override. `validate_output` lists what's missing.
- `job["output"]`, `preset["output"]` and `automation["resolved_output"]` are v2; read
  `output["video"]["codec"]`, not `output["codec"]`.
- `InvalidRequestError.errors` lists every failure of a refused spec.
- `jobs.create` and `automations.create` need a preset or a whole `output`.

| v1 | v2 | v1 default, written out in v2 |
|---|---|---|
| `mode: single` | `kind: video`, `container.format: mp4` | `single` |
| `mode: hls` | `kind: video`, `container.format: hls` | |
| `segment_seconds` | `container.segment_seconds` | `4` |
| `mode: audio` | `kind: audio` | |
| `audio.container` | `container.format` (`mp4` read as `m4a`) | `auto` → `flac` for flac, `m4a` for alac, else `mp3` |
| `mode: image` | `kind: image` | |
| `codec` | `video.codec` | `av1` |
| `quality.target` (a level) | `video.quality` | none set → `quality: "standard"` |
| `quality.crf` | `video.crf` (a level `target` is dropped: crf won) | |
| `quality.target: cbr` | `video.cbr` | |
| `quality.bitrate` | `video.cbr.bitrate` | `"standard"` |
| `quality.buffer_ms` | `video.cbr.buffer_ms` | `1000` |
| `bit_depth` | `video.bit_depth` (`auto` → `from_color`) | `from_color` |
| `color` | `video.color` | `sdr` |
| `max_fps` | `video.frame_rate.max` | `"source"` |
| `gop` | `video.gop.frames` | mp4: `{ seconds: 2 }`; hls: `"segment"` |
| `filters: "a,b"` | `video.filters: ["a", "b"]` | `[]` |
| `renditions[]` | `renditions.sizes[]` | none and no ladder → `source_size`, with the top-level `fit` and `upscale` |
| `renditions[].label` | `sizes[].label` | `by_size` |
| `renditions[].fit` / `upscale` | `sizes[].fit` / `upscale` | the top-level `fit` / `upscale`, which default to `contain` / `false` |
| `renditions[].orientation` | `sizes[].orientation` | `auto` |
| `renditions[].bitrate` | `sizes[].video.cbr.bitrate` | |
| `fit`, `upscale` (top level) | written onto every size, the ladder or the source size; dropped for audio | `contain`, `false` |
| `ladder` | `renditions.ladder` (dropped when `renditions` is non-empty, as v1 ignored it) | `max_short_side` → `1080` |
| `audio.mode: auto` | `handling: auto`, `codec: opus` (`mp3` in an mp3 container) | |
| `audio.mode: opus` \| `mp3` \| `aac` \| `flac` \| `alac` | `handling: encode`, `codec` | |
| `audio.mode: drop` | `handling: drop` | |
| `audio.bitrate` | `audio.bitrate` | `"standard"` (lossy) |
| `audio.channels` | `audio.channels` | `source` |
| `audio.he_aac` | `audio.he_aac` | `auto` |
| `audio.stereo_fallback` | `audio.stereo_fallback` | `false` (hls) |
| `audio.bit_depth` | `audio.bit_depth` | `source` (flac/alac) |
| `audio.flac_compression` | `audio.flac_compression` (`default` → `balanced`) | `balanced` (flac) |
| `subtitles: all\|none` | `subtitles.tracks` | `all` |
| `subtitles: "eng,deu"` | `subtitles.languages` | |
| `trim` | `trim` | `{ start: 0, end: "source" }`; `end` unset → `"source"` |
| `image.formats` | `image.formats` | `["avif"]` |
| `image.quality: 70` | `image.quality: { <each lossy format>: 70 }` | avif 60, webp 80, jpeg 82 |
| `image.lossless` | `image.lossless` | `false` (webp) |
| `image.keep_color_profile` | `image.color_profile: keep \| srgb` | `srgb` |
| `image.frames` | `image.frames` | `"poster"` |
| `privacy` | `privacy`, all four fields resolved | `{ preset: "strip_all" }` |

Fields v1 accepted where they didn't apply (such as `fit` on audio-only output, or
`audio.bit_depth` with AAC) have no v2 form: v2 refuses a field that doesn't apply.

## Resources

Every method has an async twin on `AsyncTranscdr`.

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
| `client.presets` | `list(category=..., compatible_with=...)`, `create`, `retrieve`, `get_version` (`slug@N`), `versions`, `update` (PATCH: `output` merges, a new version), `replace` (PUT: the whole preset), `delete` |
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
`.param`, `.details`, `.errors` and `.request_id`. `.errors` lists every failure of a refused
output spec (`[{"param", "message"}]`, the first also as `.param` and `.message`), whether the API
refused it with a 422 or the SDK found it before sending (then `.status` is `None`):

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
    client.jobs.create(input="https://example.com/in.mp4", output={"kind": "video", "privacy": {"preset": "strip_all"}})
except transcdr.InvalidRequestError as err:
    print(err.code, err.param, err.request_id)
    for problem in err.errors:
        print(problem["param"], problem["message"])
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

Every preset has a `category` (`web`, `mobile`, `streaming`, `tv`, `social`, `audio`, `archive`, `image`),
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
client.presets.replace("pre_...", name="Web 1080p", output=whole_spec)  # PUT: the whole preset
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
    preset="hls-av1-abr@1",               # resolved when each job is made; "@1" pins version 1
    output={"video": {"quality": "high"}},  # fields over the preset
    destination={"connection_id": r2["id"], "prefix": "{automation}/{date}/{stem}/"},
    after_success="delete",               # remove the source file once delivered ("keep" is the default)
    metadata={"pipeline": "ingest"},
)

automation["resolved_output"]                                         # the whole spec they resolve to now
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
