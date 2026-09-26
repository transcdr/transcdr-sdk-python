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
    "ConnectionInput",
    "Destination",
    "Delivery",
    "ConnectionKind",
    "ConnectionCapabilities",
    "Connection",
    "ConnectionTestResult",
    "RemoteObject",
    "AutomationSource",
    "Automation",
    "AutomationItem",
    "AutomationRunResult",
    "AutomationTriggerResult",
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
    "RateCard",
    "Plan",
    "CreditBuckets",
    "MonthSpend",
    "AutoRecharge",
    "Subscription",
    "CreditAccount",
    "Billing",
    "Checkout",
    "Portal",
    "CreditTransaction",
    "StatementLine",
    "Statement",
    "InvoiceLine",
    "Invoice",
    "Capabilities",
    "Status",
    "StatsTotals",
    "StatsLast24h",
    "StatsDay",
    "StatsLast30d",
    "Stats",
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


class ConnectionInput(TypedDict):
    """Read the input from one of your storage connections."""

    type: Literal["connection"]
    connection_id: str
    path: str


JobInput = Union[UrlInput, AssetInput, ConnectionInput]


class Destination(TypedDict, total=False):
    """Where to deliver a job's outputs. ``prefix`` may use templates such as
    ``{job_id}``, ``{stem}``, ``{date}``."""

    connection_id: str
    prefix: str


class Delivery(TypedDict, total=False):
    object: Literal["delivery"]
    id: str
    connection_id: str
    prefix: str
    status: Literal["waiting", "pending", "running", "succeeded", "failed"]
    files: int
    bytes: int
    attempts: int
    error: Optional[str]
    next_retry_at: Optional[str]
    created_at: str
    completed_at: Optional[str]


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
    #: Customer-safe description of what went wrong.
    message: str
    retryable: bool


class JobBilling(TypedDict, total=False):
    billable_minutes: float
    #: Rounded up to the cent.
    amount_cents: int
    #: Exact, in dollars (sub-cent).
    amount_usd: float
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
    destination: Optional[Destination]
    #: The latest delivery, on ``job.delivered`` / ``job.delivery_failed`` events.
    delivery: Optional[Delivery]
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
# Integrations: connections & automations
# --------------------------------------------------------------------------

ConnectionKind = Literal["s3", "gcs", "azure_blob", "ftp", "ftps", "sftp", "http", "webdav"]


class ConnectionCapabilities(TypedDict, total=False):
    source: bool
    destination: bool
    watch: bool


class Connection(TypedDict, total=False):
    object: Literal["connection"]
    id: str
    name: str
    kind: ConnectionKind
    #: Non-secret settings (bucket, region, endpoint, host, root, …).
    config: Dict[str, Any]
    #: Names of the secrets that are set; secret values are write-only.
    secrets_set: List[str]
    capabilities: ConnectionCapabilities
    status: Literal["untested", "ok", "error"]
    last_error: Optional[str]
    last_checked_at: Optional[str]
    created_at: str
    updated_at: str


class ConnectionTestResult(TypedDict, total=False):
    ok: bool
    error: Optional[str]
    connection: Connection


class RemoteObject(TypedDict, total=False):
    object: Literal["remote_object"]
    path: str
    size: Optional[int]
    last_modified: Optional[str]


class AutomationSource(TypedDict, total=False):
    connection_id: str
    prefix: str
    #: Glob, e.g. ``"**/*.{mp4,mov}"``.
    pattern: str


class Automation(TypedDict, total=False):
    object: Literal["automation"]
    id: str
    name: str
    enabled: bool
    trigger: Literal["watch", "hook"]
    source: AutomationSource
    poll_interval_seconds: int
    settle_seconds: int
    preset: Optional[str]
    output: Optional[OutputSpec]
    destination: Optional[Destination]
    after_success: Literal["keep", "delete"]
    priority: Literal["normal", "high"]
    metadata: Metadata
    webhook_url: Optional[str]
    #: Push endpoint for ``trigger="hook"``; shown to ``automations:write`` holders.
    hook_url: Optional[str]
    jobs_created: int
    last_polled_at: Optional[str]
    last_triggered_at: Optional[str]
    last_error: Optional[str]
    created_at: str
    updated_at: str


class AutomationItem(TypedDict, total=False):
    path: str
    size_bytes: Optional[int]
    status: str
    job_id: Optional[str]
    error: Optional[str]


class AutomationRunResult(TypedDict, total=False):
    jobs_created: int


class AutomationTriggerResult(TypedDict, total=False):
    jobs_created: int
    job_ids: List[str]


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
    #: Rounded up to the cent.
    amount_cents: int
    #: Exact, in dollars (sub-cent).
    amount_usd: float


class UsagePoint(TypedDict, total=False):
    date: str
    jobs: int
    billable_minutes: float
    amount_cents: int
    amount_usd: float


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


class RateCard(TypedDict, total=False):
    """Price per output minute in dollars; the same for every plan and codec."""

    unit: Literal["output_minute"]
    currency: str
    sd: float
    hd: float
    uhd: float
    #: What each tier covers, e.g. ``{"hd": "577p to 1440p"}``.
    tiers: Dict[str, str]


class Plan(TypedDict, total=False):
    object: Literal["plan"]
    #: ``free`` | ``pay_as_you_go`` | ``starter`` | ``growth`` | ``scale`` | ``enterprise``.
    id: str
    name: str
    tagline: str
    #: Bought as a monthly subscription through checkout.
    subscription: bool
    #: Monthly price; ``None`` means "contact us".
    price_cents: Optional[int]
    currency: str
    #: Credit each period brings. Renews each period; does not roll over.
    monthly_credit_cents: int
    #: ``monthly_credit_cents / price_cents``; ``None`` without a monthly credit.
    credit_value_ratio: Optional[float]
    trial_credit_cents: int
    trial_days: int
    rates: RateCard
    max_concurrent_jobs: int
    max_resolution: int
    max_input_bytes: int
    priority: bool
    retention_days: int
    requests_per_minute: int
    features: List[str]


class CreditBuckets(TypedDict, total=False):
    #: This period's subscription credit. Does not roll over.
    plan_usd: float
    plan_expires_at: Optional[str]
    #: Bought credit. Never expires.
    purchased_usd: float
    #: Trial and promotional credit.
    promo_usd: float
    promo_expires_at: Optional[str]


class MonthSpend(TypedDict, total=False):
    period: str
    spent_usd: float
    auto_recharged_usd: float


class AutoRecharge(TypedDict, total=False):
    enabled: bool
    threshold_cents: int
    amount_cents: int
    monthly_cap_cents: Optional[int]
    pending: bool
    last_error: Optional[str]


class Subscription(TypedDict, total=False):
    status: Optional[str]
    current_period_end: Optional[str]
    cancel_at_period_end: bool


class CreditAccount(TypedDict, total=False):
    mode: Literal["prepaid", "invoiced"]
    #: What new jobs can spend: the balance minus credit reserved for running jobs.
    available_usd: float
    balance_usd: float
    reserved_usd: float
    credit: CreditBuckets
    this_month: MonthSpend
    monthly_limit_cents: Optional[int]
    auto_recharge: AutoRecharge
    subscription: Optional[Subscription]
    #: A label for the saved card, e.g. ``"Visa •••• 4242"``.
    payment_method: Optional[str]


class Billing(TypedDict, total=False):
    object: Literal["billing"]
    plan: Plan
    rates: RateCard
    account: CreditAccount
    period: str
    period_start: str
    period_end: str
    usage_minutes: float
    usage_usd: float
    currency: str
    #: ``False`` when this installation takes no payments (credit is granted by the operator).
    payments_enabled: bool


class Checkout(TypedDict, total=False):
    object: Literal["checkout"]
    #: Send the customer here to pay; ``None`` when nothing needs paying.
    url: Optional[str]
    #: An existing subscription moved plan in place.
    changed: bool
    plan: str


class Portal(TypedDict, total=False):
    object: Literal["portal"]
    url: str


class CreditTransaction(TypedDict, total=False):
    object: Literal["credit_transaction"]
    id: str
    #: ``trial`` | ``subscription`` | ``purchase`` | ``auto_recharge`` | ``usage`` | ``adjustment`` | ``expiry``.
    kind: str
    #: ``promo`` | ``plan`` | ``purchased``; ``mixed`` for usage spanning buckets.
    bucket: str
    #: Positive adds credit, negative spends it.
    amount_usd: float
    description: str
    job_id: Optional[str]
    created_at: str


class StatementLine(TypedDict, total=False):
    description: str
    kind: str
    #: Positive adds credit, negative spends it.
    credit_usd: float
    date: str
    quantity: float
    unit: Literal["output_minute"]


class Statement(TypedDict, total=False):
    """A monthly statement: credit added and the usage drawn from it."""

    object: Literal["statement"]
    id: str
    period: str
    period_start: str
    period_end: str
    status: Literal["open", "closed"]
    lines: List[StatementLine]
    usage_minutes: float
    usage_cents: int
    currency: str


#: Monthly statements replaced invoices; kept for compatibility.
Invoice = Statement
InvoiceLine = StatementLine


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
    object: Literal["status"]
    status: str
    queue_depth: int
    running_jobs: int
    version: str


class StatsTotals(TypedDict, total=False):
    jobs_completed: int
    output_minutes: float
    source_minutes: float
    bytes_delivered: int
    renditions_delivered: int
    customers: int


class StatsLast24h(TypedDict, total=False):
    jobs_completed: int
    output_minutes: float


class StatsDay(TypedDict, total=False):
    date: str
    jobs_completed: int
    output_minutes: float


class StatsLast30d(TypedDict, total=False):
    active_customers: int


class Stats(TypedDict, total=False):
    """Public platform statistics (``GET /v1/stats``)."""

    object: Literal["stats"]
    since: str
    updated_at: str
    totals: StatsTotals
    last_24h: StatsLast24h
    last_30d: StatsLast30d
    daily: List[StatsDay]
