"""Wire types for the Transcdr v1 API.

These are :class:`typing.TypedDict` definitions mirroring ``docs/api-contract.md``.
At runtime every API object is a plain ``dict``, so ``job["status"]`` works
everywhere and type checkers see the documented fields. Objects are declared
``total=False`` because the API adds fields over time and some are only present
in certain states (``secret`` on create, ``playback_url`` once completed, …).
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

__all__ = [
    "Metadata",
    "JobStatus",
    "Stage",
    "Codec",
    "Mode",
    "Rendition",
    "Ladder",
    "Quality",
    "AudioSettings",
    "Trim",
    "OutputSpec",
    "UrlInput",
    "AssetInput",
    "JobInput",
    "AudioStream",
    "SubtitleStream",
    "MediaInfo",
    "RenditionProgress",
    "Progress",
    "JobOutput",
    "JobError",
    "JobBilling",
    "Job",
    "JobEvent",
    "SignedUrl",
    "Asset",
    "Upload",
    "Preset",
    "WebhookEndpoint",
    "WebhookDelivery",
    "Event",
    "ApiKey",
    "Organization",
    "User",
    "Me",
    "AuthResponse",
    "UsageTotals",
    "UsagePoint",
    "Usage",
    "Plan",
    "Billing",
    "InvoiceLine",
    "Invoice",
    "Capabilities",
    "Status",
    "TERMINAL_JOB_STATUSES",
]

Metadata = Dict[str, str]

JobStatus = Literal["queued", "scheduled", "running", "uploading", "completed", "failed", "canceled"]
Stage = Literal["waiting", "fetching", "probing", "encoding", "uploading", "done"]
Codec = Literal["av1", "h264", "h265"]
Mode = Literal["single", "hls"]

#: Statuses after which a job no longer changes on its own.
TERMINAL_JOB_STATUSES = frozenset({"completed", "failed", "canceled"})


# --------------------------------------------------------------------------
# Output specification
# --------------------------------------------------------------------------


class Rendition(TypedDict, total=False):
    width: int
    height: int
    #: e.g. ``"3M"`` — makes the rung rate-coded instead of quality-coded.
    bitrate: Optional[str]
    label: Optional[str]


class Ladder(TypedDict, total=False):
    max_short_side: int


class Quality(TypedDict, total=False):
    #: ``"visually_lossless" | "high" | "standard" | "low" | "vmaf=93"``
    target: str
    #: 0..63; wins over ``target``.
    crf: Optional[int]


class AudioSettings(TypedDict, total=False):
    mode: Literal["auto", "opus", "drop"]
    bitrate: Optional[str]


class Trim(TypedDict):
    start: float
    end: float


class OutputSpec(TypedDict, total=False):
    mode: Mode
    codec: Codec
    renditions: List[Rendition]
    ladder: Optional[Ladder]
    quality: Quality
    gop: Optional[int]
    segment_seconds: Optional[float]
    audio: AudioSettings
    #: ``"all" | "none" | "eng,deu"``
    subtitles: str
    color: Literal["sdr", "hdr10", "hlg", "passthrough"]
    bit_depth: Literal["auto", "8bit", "10bit"]
    max_fps: Optional[float]
    filters: Optional[str]
    trim: Optional[Trim]


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------


class UrlInput(TypedDict):
    type: Literal["url"]
    url: str


class AssetInput(TypedDict):
    type: Literal["asset"]
    asset_id: str


JobInput = Union[UrlInput, AssetInput]


class AudioStream(TypedDict, total=False):
    codec: str
    channels: int
    sample_rate: int
    language: Optional[str]


class SubtitleStream(TypedDict, total=False):
    format: str
    language: Optional[str]


class MediaInfo(TypedDict, total=False):
    container: str
    video_codec: Optional[str]
    width: int
    height: int
    frame_rate: float
    duration: float
    pixel_format: str
    bit_depth: int
    hdr: bool
    rotation: int
    audio: List[AudioStream]
    subtitles: List[SubtitleStream]
    size_bytes: Optional[int]


class RenditionProgress(TypedDict, total=False):
    index: int
    label: Optional[str]
    width: int
    height: int
    status: str
    percent: float
    frames_done: int
    frames_total: Optional[int]
    segments_written: int
    bytes_out: int


class Progress(TypedDict, total=False):
    percent: float
    stage: Stage
    renditions: List[RenditionProgress]


class JobOutput(TypedDict, total=False):
    label: str
    width: int
    height: int
    frames: int
    bytes: int
    content_type: str
    path: str
    url: str


class JobError(TypedDict, total=False):
    code: str
    message: str
    retryable: bool


class JobBilling(TypedDict, total=False):
    billable_minutes: float
    amount_cents: int
    tier: Literal["sd", "hd", "uhd"]


class Job(TypedDict, total=False):
    object: Literal["job"]
    id: str
    kind: Literal["transcode", "probe"]
    status: JobStatus
    livemode: bool
    input: JobInput
    input_info: Optional[MediaInfo]
    preset_id: Optional[str]
    output: OutputSpec
    priority: Literal["normal", "high"]
    progress: Progress
    outputs: List[JobOutput]
    playlist_url: Optional[str]
    playback_url: Optional[str]
    error: Optional[JobError]
    metadata: Metadata
    webhook_url: Optional[str]
    attempts: int
    max_attempts: int
    billing: Optional[JobBilling]
    created_at: str
    scheduled_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    updated_at: str


class JobEvent(TypedDict, total=False):
    object: Literal["job_event"]
    type: str
    message: str
    data: Any
    created_at: str


class SignedUrl(TypedDict, total=False):
    url: str
    expires_at: str


# --------------------------------------------------------------------------
# Assets & uploads
# --------------------------------------------------------------------------


class Asset(TypedDict, total=False):
    object: Literal["asset"]
    id: str
    status: Literal["pending_upload", "ready", "failed", "deleted"]
    filename: str
    content_type: str
    size_bytes: Optional[int]
    checksum_sha256: Optional[str]
    source_url: Optional[str]
    input_info: Optional[MediaInfo]
    metadata: Metadata
    download_url: str
    created_at: str


class Upload(TypedDict, total=False):
    object: Literal["upload"]
    id: str
    asset_id: str
    status: str
    upload_url: str
    upload_method: str
    upload_headers: Dict[str, str]
    expires_at: str


# --------------------------------------------------------------------------
# Presets
# --------------------------------------------------------------------------


class Preset(TypedDict, total=False):
    object: Literal["preset"]
    id: str
    slug: str
    name: str
    description: str
    system: bool
    output: OutputSpec
    metadata: Metadata
    created_at: str
    updated_at: str


# --------------------------------------------------------------------------
# Webhooks & events
# --------------------------------------------------------------------------


class WebhookEndpoint(TypedDict, total=False):
    object: Literal["webhook_endpoint"]
    id: str
    url: str
    description: str
    events: List[str]
    enabled: bool
    #: Only returned on create and rotate.
    secret: str
    created_at: str
    last_delivery_at: Optional[str]
    failure_count: int


class WebhookDelivery(TypedDict, total=False):
    object: Literal["webhook_delivery"]
    id: str
    endpoint_id: str
    event_id: str
    event_type: str
    status: Literal["pending", "succeeded", "failed"]
    attempts: int
    response_status: Optional[int]
    response_body: Optional[str]
    duration_ms: Optional[int]
    next_retry_at: Optional[str]
    created_at: str


class EventData(TypedDict, total=False):
    object: Dict[str, Any]


class Event(TypedDict, total=False):
    object: Literal["event"]
    id: str
    #: ``job.created``, ``job.completed``, ``asset.ready``, ``webhook.test``, …
    type: str
    created_at: str
    data: EventData


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------


class ApiKey(TypedDict, total=False):
    object: Literal["api_key"]
    id: str
    name: str
    prefix: str
    scopes: List[str]
    mode: Literal["live", "test"]
    last_used_at: Optional[str]
    expires_at: Optional[str]
    created_at: str
    #: Only returned on create.
    secret: str


class Organization(TypedDict, total=False):
    object: Literal["organization"]
    id: str
    name: str
    slug: str
    plan: str
    billing_email: Optional[str]
    #: Only for owners/admins holding ``org:write``.
    job_webhook_secret: str
    created_at: str


class User(TypedDict, total=False):
    object: Literal["user"]
    id: str
    name: str
    email: str
    role: Literal["owner", "admin", "member"]
    organization_id: str
    created_at: str


class Me(TypedDict, total=False):
    user: Optional[User]
    organization: Organization
    scopes: List[str]


class AuthResponse(TypedDict, total=False):
    token: str
    user: User
    organization: Organization


# --------------------------------------------------------------------------
# Usage & billing
# --------------------------------------------------------------------------


class UsageTotals(TypedDict, total=False):
    jobs: int
    billable_minutes: float
    input_minutes: float
    output_bytes: int
    amount_cents: int


class UsagePoint(TypedDict, total=False):
    date: str
    jobs: int
    billable_minutes: float
    amount_cents: int


# ``from`` is a Python keyword, so Usage uses the functional syntax.
Usage = TypedDict(
    "Usage",
    {
        "object": Literal["usage"],
        "from": str,
        "to": str,
        "granularity": Literal["day", "week", "month"],
        "totals": UsageTotals,
        "by_tier": Dict[str, float],
        "by_codec": Dict[str, float],
        "series": List[UsagePoint],
    },
    total=False,
)


class Plan(TypedDict, total=False):
    object: Literal["plan"]
    id: str
    name: str
    price_cents: int
    included_minutes: int
    overage_cents_per_minute: Dict[str, float]
    max_concurrent_jobs: int
    max_resolution: int
    priority: bool
    retention_days: int
    features: List[str]


class Billing(TypedDict, total=False):
    object: Literal["billing"]
    plan: Plan
    period_start: str
    period_end: str
    usage_minutes: float
    included_minutes: int
    overage_minutes: float
    estimated_total_cents: int
    payment_method: Optional[Dict[str, Any]]


class InvoiceLine(TypedDict, total=False):
    description: str
    quantity: float
    unit_amount_cents: float
    amount_cents: int


class Invoice(TypedDict, total=False):
    object: Literal["invoice"]
    id: str
    period_start: str
    period_end: str
    status: Literal["draft", "open", "paid"]
    lines: List[InvoiceLine]
    total_cents: int
    currency: str


# --------------------------------------------------------------------------
# Public service info
# --------------------------------------------------------------------------


class Capabilities(TypedDict, total=False):
    codecs: List[str]
    modes: List[str]
    color: List[str]
    limits: Dict[str, Any]
    filters: List[str]
    system_presets: List[Preset]


class Status(TypedDict, total=False):
    status: str
    queue_depth: int
    running_jobs: int
