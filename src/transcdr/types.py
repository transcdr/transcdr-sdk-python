"""Wire types for the Transcdr v1 API, with output spec v2.

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
    "Kind",
    "ContainerFormat",
    "VideoBitDepth",
    "Color",
    "AudioHandling",
    "AudioCodec",
    "AudioChannels",
    "AudioBitDepth",
    "FlacCompression",
    "HeAac",
    "Fit",
    "Orientation",
    "ColorProfile",
    "ImageFormat",
    "ImageTier",
    "PrivacyPresetName",
    "LocationHandling",
    "CaptureTimeHandling",
    "DeviceHandling",
    "DescriptiveHandling",
    "Source",
    "Container",
    "FrameRate",
    "GopFrames",
    "GopSeconds",
    "Gop",
    "Cbr",
    "VideoQuality",
    "VideoCrf",
    "VideoCbr",
    "Video",
    "AudioTrack",
    "AudioDrop",
    "Audio",
    "FramesCount",
    "FramesAt",
    "ImageFrames",
    "ImageSettings",
    "SizeCbr",
    "SizeVideo",
    "Size",
    "Ladder",
    "SourceSize",
    "RenditionSizes",
    "RenditionLadder",
    "RenditionSourceSize",
    "Renditions",
    "SubtitleTracks",
    "SubtitleLanguages",
    "Subtitles",
    "Trim",
    "PrivacyPreset",
    "PrivacyFields",
    "Privacy",
    "VideoOutput",
    "AudioOutput",
    "ImageOutput",
    "OutputSpec",
    "OutputOverrides",
    "FieldError",
    "PresetProvenance",
    "PresetVersion",
    "OutputCapabilities",
    "OutputField",
    "OutputGroup",
    "OutputContainerInfo",
    "OutputAudioCodecInfo",
    "OutputCompatibility",
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
    "PresetCategory",
    "Platform",
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
    "ImageRateCard",
    "ImagesByTier",
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
    "ImageFormatInfo",
    "ImageLimits",
    "Status",
    "StatsTotals",
    "StatsLast24h",
    "StatsDay",
    "StatsLast30d",
    "Stats",
    "TERMINAL_JOB_STATUSES",
    "WebhookEndpointType",
    "WebhookAwsConfig",
    "WebhookAwsParams",
    "StorageConnectionKind",
    "MessagingConnectionKind",
    "MESSAGING_CONNECTION_KINDS",
    "CheckStep",
    "CheckIdentity",
    "CheckRoles",
    "CheckSetup",
    "ConnectionCheck",
    "WebhookCheck",
    "MembershipOrganization",
    "Membership",
    "InputReportTotals",
    "InputTotals",
    "InputKind",
    "InputPoint",
    "InputReport",
    "AnnouncementLink",
    "ServiceCredit",
    "Announcement",
]

Metadata = Dict[str, str]

JobStatus = Literal["queued", "scheduled", "running", "uploading", "completed", "failed", "canceled"]
Stage = Literal["waiting", "fetching", "probing", "encoding", "uploading", "done"]
Codec = Literal["av1", "h264", "h265"]
#: What a job produces: ``video`` (an MP4 per size, or an HLS package),
#: ``audio`` (the audio alone as one ``.mp3``, ``.flac`` or ``.m4a``) or
#: ``image`` (still images of an image, or stills from a video).
Kind = Literal["video", "audio", "image"]
#: The file or package. Kind ``video``: ``mp4`` or ``hls``. Kind ``audio``:
#: ``mp3`` (MP3 only), ``flac`` (FLAC only) or ``m4a`` (any codec).
ContainerFormat = Literal["mp4", "hls", "mp3", "flac", "m4a"]
#: An image output format: ``avif`` (the smallest), ``webp``, ``jpeg`` or
#: ``png`` (always lossless).
ImageFormat = Literal["avif", "webp", "jpeg", "png"]
#: An output image's price tier, by the pixels it came out at.
ImageTier = Literal["up_to_1mp", "up_to_4mp", "over_4mp"]
#: ``from_color``: 8-bit for ``sdr``, 10-bit for ``hdr10`` and ``hlg``, the
#: source's for ``passthrough``. HDR needs ``from_color`` or ``10bit``;
#: ``10bit`` is not offered with H.264.
VideoBitDepth = Literal["from_color", "8bit", "10bit"]
#: ``hdr10`` and ``hlg`` need a paid plan.
Color = Literal["sdr", "hdr10", "hlg", "passthrough"]
#: ``auto``: keep the source's audio where the container carries it
#: unchanged, otherwise make it ``codec``. ``encode``: make it ``codec`` (a
#: source already in it, with nothing else changed, is copied). ``drop``: no
#: audio track (kind ``video`` only).
AudioHandling = Literal["auto", "encode", "drop"]
#: ``aac`` is AAC-LC, the codec that plays on the most devices. ``mp3`` is
#: constant bit rate, stereo at most, not for HLS. ``flac`` and ``alac`` are
#: lossless and take no bitrate. An ``.mp3`` holds MP3 only, a ``.flac``
#: FLAC only.
AudioCodec = Literal["opus", "mp3", "aac", "flac", "alac"]
#: ``source`` keeps the source's layout; the rest downmix and never upmix.
#: MP3 carries ``source`` (folded to stereo at most), ``mono`` or ``stereo``.
AudioChannels = Literal["source", "mono", "stereo", "5.1", "7.1"]
#: FLAC and ALAC sample depth. ``source`` is 16-bit for a 16-bit or lossy
#: source, 24-bit for a deeper one.
AudioBitDepth = Literal["source", "16", "24"]
#: FLAC compression effort: the same audio either way, a smaller file for
#: more work.
FlacCompression = Literal["fast", "balanced", "best"]
#: What an HE-AAC (or HE-AAC v2) source becomes. HE-AAC is decoded only as
#: its AAC-LC core: spectral band replication and parametric stereo are not
#: decoded, so the core has half the stream's rate, less bandwidth and, for
#: v2, one channel. ``auto`` passes it through when only a codec change is
#: asked and decodes its core when the job needs PCM (a downmix, an ``.mp3``
#: or ``.flac`` file); ``passthrough`` never decodes it, and a job that would
#: need it decoded fails; ``core`` decodes its core whenever another codec
#: is asked. AAC-LC is decoded in full regardless.
HeAac = Literal["auto", "passthrough", "core"]
#: How the picture meets a size's box. ``contain`` keeps its shape inside
#: the box; ``cover`` fills the box and centre-crops; ``pad`` keeps its shape
#: and adds black bars to exactly the box; ``stretch`` distorts it to
#: exactly the box.
Fit = Literal["contain", "cover", "pad", "stretch"]
#: ``auto``: the box turns to the picture's orientation, so 1920x1080 on a
#: portrait video is 1080x1920. ``fixed``: the box is used as written.
Orientation = Literal["auto", "fixed"]
#: ``srgb`` converts the pixels to sRGB; ``keep`` keeps the source's colour
#: profile (PNG, JPEG, WebP).
ColorProfile = Literal["srgb", "keep"]
PrivacyPresetName = Literal["strip_all", "strip_location", "keep_all"]
#: ``approximate``: rounded to 2 decimal places (about 1 km), no altitude,
#: no place name.
LocationHandling = Literal["strip", "approximate", "keep"]
#: ``date``: the day, the time of day zeroed.
CaptureTimeHandling = Literal["strip", "date", "keep"]
#: ``keep``: make, model, software and lens. ``keep_all``: also serial
#: numbers and the owner name.
DeviceHandling = Literal["strip", "keep", "keep_all"]
DescriptiveHandling = Literal["strip", "keep"]
#: A value that follows the source, written out.
Source = Literal["source"]

#: Statuses after which a job no longer changes on its own.
TERMINAL_JOB_STATUSES = frozenset({"completed", "failed", "canceled"})


# --------------------------------------------------------------------------
# Output specification (v2)
#
# A spec is declared in sections and nothing has a default: every field its
# kind, container, codec and handling need is stated. Fields every spec of a
# kind needs are required keys here; fields needed only under a condition
# (an HLS container's ``segment_seconds``, a lossy codec's ``bitrate``, ...)
# are optional keys, checked by :func:`transcdr.validate_output` against
# the API's table. "Exactly one of" choices are unions.
# --------------------------------------------------------------------------


class _ContainerRequired(TypedDict):
    format: ContainerFormat


class Container(_ContainerRequired, total=False):
    #: Required for ``hls``, refused otherwise: seconds per segment, 1-20.
    segment_seconds: float


class FrameRate(TypedDict):
    #: A cap in frames per second, 1-240, or ``"source"``: the source's rate,
    #: not capped.
    max: Union[float, Source]


class GopFrames(TypedDict):
    #: A keyframe every N frames, 1-1200.
    frames: int


class GopSeconds(TypedDict):
    #: A keyframe every N seconds, 0.1-60.
    seconds: float


#: The keyframe interval. ``"segment"`` (``hls`` only): one keyframe at the
#: start of each segment and none inside it.
Gop = Union[GopFrames, GopSeconds, Literal["segment"]]


class Cbr(TypedDict):
    #: 100k to 200M, e.g. ``"5M"``, or ``"standard"``: a rate for each size
    #: by codec, short side and frame rate.
    bitrate: str
    #: The rate buffer, 100-10000 ms.
    buffer_ms: int


class _VideoBase(TypedDict):
    #: ``h265`` needs a paid plan.
    codec: Codec
    bit_depth: VideoBitDepth
    color: Color
    frame_rate: FrameRate
    gop: Gop
    #: A filter chain, one filter per entry, e.g. ``["crop=1280:720",
    #: "hflip"]``; ``[]`` for none.
    filters: List[str]


class VideoQuality(_VideoBase):
    #: ``visually_lossless``, ``high``, ``standard``, ``low`` or ``vmaf=N``.
    quality: str


class VideoCrf(_VideoBase):
    #: A constant rate factor, 0-63.
    crf: int


class VideoCbr(_VideoBase):
    #: Every size at a constant bit rate.
    cbr: Cbr


#: The video track: exactly one of ``quality``, ``crf`` and ``cbr``.
Video = Union[VideoQuality, VideoCrf, VideoCbr]


class AudioDrop(TypedDict):
    """No audio track (kind ``video`` only)."""

    handling: Literal["drop"]


class _AudioTrackRequired(TypedDict):
    handling: Literal["auto", "encode"]
    #: With ``encode``, the codec made. With ``auto``, what audio the
    #: container cannot carry becomes (``opus``; ``mp3`` in an ``.mp3``).
    codec: AudioCodec
    channels: AudioChannels
    he_aac: HeAac


class AudioTrack(_AudioTrackRequired, total=False):
    """An audio track. The optional keys are required under a condition."""

    #: Required with ``opus``, ``mp3`` and ``aac``, refused otherwise:
    #: 6k-512k (MP3: 32k, 40k, 48k, 56k, 64k, 80k, 96k, 112k, 128k, 160k,
    #: 192k, 224k, 256k or 320k; AAC: 8k-288k per main channel), or
    #: ``"standard"``: AAC 64k mono, 128k stereo, 384k 5.1, 512k 7.1; Opus
    #: 96k stereo, 320k 5.1, 416k 7.1; MP3 64k mono, 128k stereo.
    bitrate: str
    #: Required with an ``hls`` container: a stereo downmix beside surround
    #: audio. ``True`` needs ``channels`` ``source``, ``5.1`` or ``7.1``.
    stereo_fallback: bool
    #: Required with ``flac`` and ``alac``.
    bit_depth: AudioBitDepth
    #: Required with ``flac``.
    flac_compression: FlacCompression


#: The audio: a track, or none.
Audio = Union[AudioTrack, AudioDrop]


class FramesCount(TypedDict):
    #: 1-100 stills, evenly spaced through a video input.
    count: int


class FramesAt(TypedDict):
    #: 1-100 times, in seconds, in a video input.
    at_seconds: List[float]


#: Which stills. ``"poster"``: an image input as it is; a video's frame 10%
#: of the way in. ``count`` and ``at_seconds`` take a video input only.
ImageFrames = Union[Literal["poster"], FramesCount, FramesAt]


class _ImageRequired(TypedDict):
    #: 1 to 4 distinct formats; every size is made in each.
    formats: List[ImageFormat]
    color_profile: ColorProfile
    frames: ImageFrames


class ImageSettings(_ImageRequired, total=False):
    """Still images. The optional keys are required under a condition."""

    #: Required when ``webp`` is made: lossless WebP.
    lossless: bool
    #: Required when a lossy format is made (``avif``, ``jpeg``, ``webp``
    #: without ``lossless``): one entry, 1-100, for each lossy format made
    #: and no others, e.g. ``{"avif": 60, "jpeg": 82}``.
    quality: Dict[str, int]


class SizeCbr(TypedDict):
    bitrate: str


class SizeVideo(TypedDict):
    cbr: SizeCbr


class _SizeRequired(TypedDict):
    #: 1-32 of ``A-Z a-z 0-9 - _``, or ``"by_size"``: ``<short side>p`` of the
    #: size it comes out at (images: ``<width>x<height>``).
    label: str
    #: The box's width, a maximum: video 64-7680 and even; image 16-8192.
    width: int
    #: The box's height: video 64-4320 and even; image 16-8192.
    height: int
    fit: Fit
    orientation: Orientation
    #: Let the output be larger than the source.
    upscale: bool


class Size(_SizeRequired, total=False):
    """One output size: a box the picture is fitted into, not the output
    size. Each output reports the size it came out at."""

    #: With ``video.cbr`` only: this size's own rate over
    #: ``video.cbr.bitrate``. The response writes it on every size.
    video: SizeVideo


class Ladder(TypedDict):
    """An automatic ladder of the standard short sides up to
    ``max_short_side``, never above the source (kind ``video`` only)."""

    max_short_side: int
    fit: Fit
    upscale: bool


class SourceSize(TypedDict):
    """One output at the source's size."""

    label: str
    fit: Fit
    upscale: bool


class RenditionSizes(TypedDict):
    sizes: List[Size]


class RenditionLadder(TypedDict):
    ladder: Ladder


class RenditionSourceSize(TypedDict):
    source_size: SourceSize


#: The sizes produced: exactly one of ``sizes``, ``ladder`` and ``source_size``.
Renditions = Union[RenditionSizes, RenditionLadder, RenditionSourceSize]


class SubtitleTracks(TypedDict):
    #: ``all``: every subtitle track of the source; ``none``: none.
    tracks: Literal["all", "none"]


class SubtitleLanguages(TypedDict):
    #: ISO 639 codes, e.g. ``["eng", "deu"]``.
    languages: List[str]


#: Which subtitle tracks are carried: exactly one of ``tracks`` and ``languages``.
Subtitles = Union[SubtitleTracks, SubtitleLanguages]


class Trim(TypedDict):
    #: Seconds from the start, >= 0.
    start: float
    #: Seconds from the start, after ``start``; or ``"source"``: the end.
    end: Union[float, Source]


class _PrivacyPresetRequired(TypedDict):
    preset: PrivacyPresetName


class PrivacyPreset(_PrivacyPresetRequired, total=False):
    """A privacy preset, refined by any of the four categories given beside
    it: ``strip_all`` strips every category, ``strip_location`` only the
    location, ``keep_all`` keeps them all."""

    location: LocationHandling
    capture_time: CaptureTimeHandling
    device: DeviceHandling
    descriptive: DescriptiveHandling


class PrivacyFields(TypedDict):
    """Each category stated. Responses always carry this form."""

    location: LocationHandling
    capture_time: CaptureTimeHandling
    device: DeviceHandling
    descriptive: DescriptiveHandling


#: Which identifying metadata survives: a preset (with any categories over
#: it), or all four categories.
Privacy = Union[PrivacyPreset, PrivacyFields]


class VideoOutput(TypedDict):
    kind: Literal["video"]
    container: Container
    video: Video
    audio: Audio
    renditions: Renditions
    subtitles: Subtitles
    trim: Trim
    privacy: Privacy


class AudioOutput(TypedDict):
    kind: Literal["audio"]
    container: Container
    audio: AudioTrack
    privacy: Privacy


class ImageOutput(TypedDict):
    kind: Literal["image"]
    image: ImageSettings
    renditions: Renditions
    privacy: Privacy


#: A whole output spec: what a job produces, every field stated. Jobs,
#: presets and automations return it resolved.
OutputSpec = Union[VideoOutput, AudioOutput, ImageOutput]


class OutputOverrides(TypedDict, total=False):
    """Fields over a preset (a job's or automation's ``output`` with a
    ``preset``, or a ``PATCH`` of a preset's output). Any subset: objects
    merge key by key, scalars and lists replace, one choice of an exclusive
    group (``crf`` over ``quality``, ``ladder`` over ``sizes``, ``languages``
    over ``tracks``) replaces the others, ``None`` removes a field, and
    ``kind`` cannot change. The result must be a whole, valid spec: after
    changing ``container.format`` to ``mp4``, send ``segment_seconds: None``
    too."""

    kind: Kind
    container: Optional[Dict[str, Any]]
    video: Optional[Dict[str, Any]]
    audio: Optional[Dict[str, Any]]
    image: Optional[Dict[str, Any]]
    renditions: Optional[Dict[str, Any]]
    subtitles: Optional[Dict[str, Any]]
    trim: Optional[Dict[str, Any]]
    privacy: Optional[Dict[str, Any]]


class PresetProvenance(TypedDict, total=False):
    """Where a job's spec came from."""

    #: The preset's id (``pre_...``, or a system preset's slug).
    id: str
    #: Its slug.
    slug: str
    #: The version it resolved to.
    version: int
    #: The request's ``output`` over it, in v2 form; ``None`` when none.
    overrides: Optional[OutputOverrides]


class FieldError(TypedDict):
    """One failure of a refused output spec: ``output.<path>`` and why."""

    param: str
    message: str


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
    #: Non-square pixels only: the size the picture is shown at (720x576 at
    #: 64:45 is shown 1024x576).
    display_width: int
    display_height: int


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
    #: Image output: the file's format.
    format: ImageFormat
    #: Image output: the rendition it was made for (its label, or the size it
    #: came out at).
    rendition: str
    #: Image output of a video with several stills: which still, from 1.
    frame: int
    #: Image output of a video: the still's time, in seconds.
    at_seconds: float


class JobError(TypedDict, total=False):
    code: str
    #: Customer-safe description of what went wrong.
    message: str
    retryable: bool


class JobBilling(TypedDict, total=False):
    billable_minutes: float
    #: Image output: the images billed (an image job bills no minutes).
    billable_images: int
    #: Rounded up to the cent.
    amount_cents: int
    #: Exact, in dollars (sub-cent).
    amount_usd: float
    #: ``sd``, ``hd`` or ``uhd``; an image job's is an :data:`ImageTier`.
    tier: Literal["sd", "hd", "uhd", "up_to_1mp", "up_to_4mp", "over_4mp"]


class Job(TypedDict, total=False):
    object: Literal["job"]
    id: str
    kind: Literal["transcode", "probe"]
    status: JobStatus
    livemode: bool
    input: JobInput
    input_info: Optional[MediaInfo]
    preset_id: Optional[str]
    #: Where the spec came from: the preset version and the request's
    #: ``output`` over it. ``None`` for a job sent a whole spec.
    preset: Optional[PresetProvenance]
    #: The resolved, complete spec: what runs, and what a rerun uses.
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


class SecretFingerprint(TypedDict):
    """A write-only secret that is set. The fingerprint changes when the
    secret changes and says nothing else (it is keyed by the server and bound
    to the object and field): compare it with an earlier read to notice a
    change made elsewhere."""

    set: bool
    #: ``hmac-sha256:<12 hex>``.
    fingerprint: str


# --------------------------------------------------------------------------
# Presets
# --------------------------------------------------------------------------


PresetCategory = Literal["web", "mobile", "streaming", "tv", "social", "audio", "archive", "image"]
"""The group a preset is shown in. More may be added: treat an unknown one as
uncategorised. ``audio`` is reserved for audio-only presets and ``image`` for
still images."""

Platform = Literal["web", "ios", "android", "smart_tv", "legacy", "editing"]
"""Where an output plays. More may be added: ignore unknown ones."""


class Preset(TypedDict, total=False):
    object: Literal["preset"]
    id: str
    slug: str
    name: str
    description: str
    system: bool
    category: PresetCategory
    compatibility: List[Platform]
    """Where the output plays: derived from ``output`` unless the preset sets its own."""
    compatibility_notes: Dict[str, str]
    """Minimum versions and conditions, by platform in ``compatibility``."""
    version: int
    """Its latest version. Editing its output adds one; a version never changes."""
    output: OutputSpec
    """The latest version's spec (or version N's, from ``get_version``)."""
    metadata: Metadata
    created_at: str
    updated_at: str


class PresetVersion(TypedDict, total=False):
    """One version of a preset: a whole spec that never changes."""

    object: Literal["preset_version"]
    version: int
    output: OutputSpec
    #: ``None`` for system presets.
    created_at: Optional[str]


# --------------------------------------------------------------------------
# Webhooks & events
# --------------------------------------------------------------------------


WebhookEndpointType = Literal["https", "sns", "sqs"]


class WebhookAwsConfig(TypedDict, total=False):
    """The AWS side of an ``sns`` or ``sqs`` destination. The secret access key
    is never returned."""

    region: str
    access_key_id: str
    #: An SNS/SQS-compatible service endpoint, when not AWS itself.
    endpoint: Optional[str]
    #: FIFO topics and queues only.
    message_group_id: Optional[str]
    secret_access_key_set: bool


class WebhookAwsParams(TypedDict, total=False):
    """AWS settings as sent. On create ``access_key_id`` and
    ``secret_access_key`` are required; on update an omitted secret is kept."""

    access_key_id: str
    secret_access_key: str
    #: Read from the topic ARN or queue URL when omitted.
    region: str
    #: An SNS-compatible service endpoint; ``None`` on update clears it.
    endpoint: Optional[str]
    #: FIFO targets; default ``"transcdr"``. ``None`` on update clears it.
    message_group_id: Optional[str]


class WebhookEndpoint(TypedDict, total=False):
    """An event destination: an HTTPS URL, an Amazon SNS topic or an Amazon SQS
    queue, or a messaging connection."""

    object: Literal["webhook_endpoint"]
    id: str
    #: ``https`` for endpoints created before destinations had a type.
    type: WebhookEndpointType
    #: The HTTPS URL; for ``sns``/``sqs`` the topic ARN or queue URL.
    url: str
    topic_arn: Optional[str]
    queue_url: Optional[str]
    aws: Optional[WebhookAwsConfig]
    description: str
    events: List[str]
    enabled: bool
    #: Only returned on create and rotate.
    secret: str
    #: The write-only secrets that are set, with their fingerprints:
    #: ``secret`` and, for sns/sqs, ``secret_access_key``.
    secrets: Dict[str, SecretFingerprint]
    created_at: str
    updated_at: str
    last_delivery_at: Optional[str]
    failure_count: int
    #: The messaging connection (``sqs``, ``sns``, ``webhook``) events go
    #: through, or ``None`` when the endpoint has its own target.
    connection_id: Optional[str]


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

StorageConnectionKind = Literal["s3", "gcs", "azure_blob", "ftp", "ftps", "sftp", "http", "webdav"]
#: Receive events; an ``sqs`` connection can also trigger automations.
MessagingConnectionKind = Literal["sqs", "sns", "webhook"]
ConnectionKind = Literal[
    "s3", "gcs", "azure_blob", "ftp", "ftps", "sftp", "http", "webdav", "sqs", "sns", "webhook"
]

#: The messaging kinds: never a job input, a destination or an automation source.
MESSAGING_CONNECTION_KINDS = frozenset({"sqs", "sns", "webhook"})


class ConnectionCapabilities(TypedDict, total=False):
    source: bool
    destination: bool
    watch: bool
    #: It can trigger ``queue`` automations (``sqs``).
    trigger: bool
    #: It can receive events (messaging kinds).
    events: bool


class Connection(TypedDict, total=False):
    object: Literal["connection"]
    id: str
    name: str
    kind: ConnectionKind
    #: Non-secret settings (bucket, region, endpoint, host, root, queue_url, …).
    config: Dict[str, Any]
    #: Names of the secrets that are set; secret values are write-only.
    secrets_set: List[str]
    #: The secrets that are set, with their fingerprints.
    secrets: Dict[str, SecretFingerprint]
    capabilities: ConnectionCapabilities
    status: Literal["untested", "ok", "error"]
    #: ``storage`` or ``messaging``.
    #: (``class`` is a keyword: read it as ``connection["class"]``.)
    enabled: bool
    #: Transient failures in a row; any success resets it.
    failure_count: int
    #: ``"<activity>: <error>"`` or ``"Disabled by hand."``.
    disabled_reason: Optional[str]
    disabled_at: Optional[str]
    last_error: Optional[str]
    last_checked_at: Optional[str]
    created_at: str
    updated_at: str


class CheckStep(TypedDict, total=False):
    """One step of a live check. Connections: ``settings``, ``connect``,
    ``identity``, ``list``, ``write``, ``read``, ``delete``. Destinations:
    ``identity``, then ``deliver``, ``publish`` or ``send``."""

    id: str
    label: str
    status: Literal["passed", "failed", "skipped"]
    #: What happened, or the provider's error.
    detail: Optional[str]
    #: On failure: what to change.
    hint: Optional[str]
    duration_ms: Optional[int]


class CheckIdentity(TypedDict, total=False):
    """Who the credentials sign in as. ``provider`` is ``aws``, ``gcp``,
    ``azure``, ``s3_compatible`` or ``sftp``; the other fields depend on it."""

    provider: str
    arn: str
    account: str
    service_account: str
    project: str
    auth: str
    access_key_id: str
    user: str
    server: str


class CheckRoles(TypedDict, total=False):
    source: bool
    watch_folder: bool
    destination: bool
    #: ``sqs``: the queue can be read, so it can trigger automations.
    trigger: bool
    #: ``sns``, ``webhook``: the test event got through.
    notifications: bool


#: Provider-specific setup: ``summary``, ``iam_policy``, ``queue_policy_for_s3``,
#: ``queue_policy_for_sns``, ``s3_notification``, ``notes``, ``role``, ``command``, …
CheckSetup = Dict[str, Any]


class ConnectionCheck(TypedDict, total=False):
    object: Literal["connection_check"]
    #: Every step passed (skipped steps do not count against it).
    ok: bool
    steps: List[CheckStep]
    identity: Optional[CheckIdentity]
    setup: Optional[CheckSetup]
    roles: CheckRoles
    #: Saved connections only: the connection with its updated status.
    connection: "Connection"


class WebhookCheck(TypedDict, total=False):
    object: Literal["webhook_check"]
    ok: bool
    steps: List[CheckStep]
    identity: Optional[CheckIdentity]
    setup: Optional[CheckSetup]
    roles: CheckRoles
    #: Saved endpoints only.
    endpoint: WebhookEndpoint


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
    trigger: Literal["watch", "hook", "queue"]
    #: ``queue``: the ``sqs`` connection it consumes.
    trigger_connection_id: Optional[str]
    source: AutomationSource
    poll_interval_seconds: int
    settle_seconds: int
    #: ``slug``, ``slug@N`` or an id; resolved each time a job is made.
    preset: Optional[str]
    #: The fields over the preset, as stored.
    output: Optional[OutputOverrides]
    #: The whole spec ``preset`` and ``output`` resolve to now.
    resolved_output: Optional[OutputSpec]
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
    job_ids: List[str]
    #: Queue automations: messages read in this batch.
    messages_received: int
    #: Queue automations: messages handled and removed from the queue.
    messages_deleted: int


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
    #: Always ``None`` on keys the API returns: a revoked key is 404.
    revoked_at: Optional[str]
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
    #: The full plan object for ``plan``.
    plan_details: "Plan"
    #: Suspended organizations cannot create jobs.
    suspended: bool
    created_at: str


class User(TypedDict, total=False):
    object: Literal["user"]
    id: str
    name: str
    email: str
    role: Literal["owner", "admin", "member"]
    organization_id: str
    created_at: str


class MembershipOrganization(TypedDict, total=False):
    id: str
    name: str
    slug: str
    plan: str


class Membership(TypedDict, total=False):
    """An organization the user belongs to, with the user's role there."""

    object: Literal["membership"]
    organization: MembershipOrganization
    role: Literal["owner", "admin", "member"]
    created_at: str


class Me(TypedDict, total=False):
    object: Literal["me"]
    #: The signed-in user, or for an API key the user who created the key. A
    #: user does not mean a session: use :func:`is_session`.
    user: Optional[User]
    organization: Organization
    #: Every organization the user belongs to (sessions); always empty for API keys.
    organizations: List[Membership]
    #: The token presented: a session's ``prefix`` starts ``tds_``, an API
    #: key's ``tdk_live_`` or ``tdk_test_``.
    api_key: Optional[ApiKey]
    scopes: List[str]
    #: ``False`` for test-mode keys.
    livemode: bool


def is_session(me: Me) -> bool:
    """Whether ``me`` describes a session token (a signed-in user) rather
    than an API key."""
    prefix = (me.get("api_key") or {}).get("prefix")
    if prefix:
        return prefix.startswith("tds_")
    # Older servers: a session lists its memberships (never empty); an API key none.
    return bool(me.get("organizations"))


class AuthResponse(TypedDict, total=False):
    token: str
    #: ``role`` and ``organization_id`` are the user's in ``organization``.
    user: User
    #: The organization the token belongs to.
    organization: Organization
    #: Every organization the user belongs to.
    organizations: List[Membership]


# --------------------------------------------------------------------------
# Usage & billing
# --------------------------------------------------------------------------


class UsageTotals(TypedDict, total=False):
    jobs: int
    billable_minutes: float
    #: Output images billed.
    billable_images: int
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
    billable_images: int
    amount_cents: int
    amount_usd: float


class ImagesByTier(TypedDict, total=False):
    """Output images, by tier."""

    up_to_1mp: int
    up_to_4mp: int
    over_4mp: int


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
        # Output images billed, by tier.
        "by_image_tier": ImagesByTier,
        # Minutes by codec (image jobs are not counted here).
        "by_codec": Dict[str, float],
        "series": List[UsagePoint],
    },
    total=False,
)


class InputReportTotals(TypedDict, total=False):
    """Totals for a set of inputs."""

    files: int
    size_bytes: int
    input_minutes: float
    billable_minutes: float


class InputKind(InputReportTotals, total=False):
    """One kind of input, ``container/codec``: ``mp4/h264``, ``mkv/hevc``, ``m4a/audio``."""

    #: ``container/codec``, or ``other`` for the kinds past the seven most common.
    kind: str
    container: Optional[str]
    video_codec: Optional[str]


class InputPoint(InputReportTotals, total=False):
    """The inputs of one kind in one duration × size bucket (log scale, four per decade)."""

    kind: str
    #: Where to plot the point.
    mean_duration_seconds: float
    mean_size_bytes: float
    #: The bucket's bounds, ``[low, high)``.
    duration_range: List[float]
    size_range: List[float]


InputTotals = InputReportTotals

# ``from`` is a Python keyword, so InputReport uses the functional syntax.
InputReport = TypedDict(
    "InputReport",
    {
        "object": Literal["input_report"],
        "from": str,
        "to": str,
        #: Inputs not probed yet, or with no duration or size: counted, not plotted.
        "unmeasured": int,
        #: Most files first; ``other`` last.
        "kinds": List[InputKind],
        "points": List[InputPoint],
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


class ImageRateCard(TypedDict, total=False):
    """Price per output image in dollars, by the pixels it came out at."""

    unit: Literal["output_image"]
    currency: str
    up_to_1mp: float
    up_to_4mp: float
    over_4mp: float
    #: What each tier covers, e.g. ``{"up_to_1mp": "up to 1 megapixel"}``.
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
    #: Image output prices.
    image_rates: ImageRateCard
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
    #: Image output prices.
    image_rates: ImageRateCard
    account: CreditAccount
    period: str
    period_start: str
    period_end: str
    usage_minutes: float
    #: Output images billed this period.
    usage_images: int
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
    unit: Literal["output_minute", "output_image"]


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
    #: Output images billed this period.
    usage_images: int
    usage_cents: int
    currency: str


#: Monthly statements replaced invoices; kept for compatibility.
Invoice = Statement
InvoiceLine = StatementLine


# --------------------------------------------------------------------------
# Public service info
# --------------------------------------------------------------------------


class ImageFormatInfo(TypedDict, total=False):
    """An image output format, as ``capabilities.retrieve()`` lists it."""

    id: str
    name: str
    default: bool
    #: Takes ``image.quality``.
    lossy: bool
    #: Can be lossless (PNG always, WebP with ``image.lossless``).
    lossless: bool
    #: Keeps transparency.
    alpha: bool
    #: A suggested ``image.quality`` for this format (lossy formats only).
    #: A v2 spec always states its quality: nothing is filled in.
    default_quality: int


class ImageLimits(TypedDict, total=False):
    """Image output limits (``limits["image"]``)."""

    #: Smallest rendition side.
    min_dimension: int
    #: Largest rendition side.
    max_dimension: int
    #: Most files one job may make: stills x renditions x formats.
    max_outputs: int
    #: Most stills one video may give.
    max_frames: int
    #: Largest image input.
    max_input_megapixels: int


class OutputField(TypedDict, total=False):
    """One field of the output spec. It is required (or, when ``required`` is
    false, allowed) when any object in ``when`` matches; an object matches
    when every path in it has one of the listed values (``"*"``: present,
    ``"!"``: absent). Outside ``when`` it is refused."""

    #: Relative to ``output``; ``[]`` stands for each entry of a list.
    path: str
    required: bool
    when: List[Dict[str, List[str]]]
    #: ``{"type": "enum", "values": [...]}``, ``{"type": "number", "min", "max"}``, ...
    shape: Dict[str, Any]
    #: Its exclusive group (``output.groups``), if it is one of several choices.
    group: Optional[str]
    description: str


class OutputGroup(TypedDict, total=False):
    """Choices of which exactly one is given whenever ``when`` matches."""

    name: str
    members: List[str]
    when: List[Dict[str, List[str]]]
    exactly_one: bool


class OutputContainerInfo(TypedDict, total=False):
    id: ContainerFormat
    kind: Kind
    #: The audio codecs it holds.
    audio_codecs: List[AudioCodec]


class OutputAudioCodecInfo(TypedDict, total=False):
    id: AudioCodec
    name: str
    lossless: bool
    max_channels: int
    #: The fixed rates it takes (MP3), else ``None``.
    bitrates: Optional[List[str]]


class OutputCompatibility(TypedDict, total=False):
    #: How v1 requests are read.
    v1_requests: str
    #: ``{"header", "value", "query", "sunset"}``: how a client not yet on
    #: v2 asks for v1 responses, and when that ends.
    v1_responses: Dict[str, str]


class OutputCapabilities(TypedDict, total=False):
    #: ``2``.
    version: int
    kinds: List[Kind]
    fields: List[OutputField]
    groups: List[OutputGroup]
    #: How ``when`` is read, in words.
    conditions: str
    containers: List[OutputContainerInfo]
    audio_codecs: List[OutputAudioCodecInfo]
    #: ``"audio.bitrate: standard"`` -> what it resolves to.
    follow_values: Dict[str, str]
    compatibility: OutputCompatibility


class Capabilities(TypedDict, total=False):
    #: ``[{"id": "av1", "name": "AV1", "default": True, "hdr": True, "bit_depths": [8, 10], …}]``
    codecs: List[Dict[str, Any]]
    #: ``[{"id": "hls", "description": "…"}]``
    modes: List[Dict[str, Any]]
    audio: List[str]
    bit_depth: List[str]
    color: List[str]
    quality_targets: List[str]
    filters: List[str]
    input_containers: List[str]
    input_video_codecs: List[str]
    input_audio_codecs: List[str]
    #: Image output formats; empty when image output is unavailable.
    image_formats: List[ImageFormatInfo]
    #: Image inputs read: ``jpeg``, ``png``, ``webp``, ``avif``, ``gif`` (first
    #: frame), ``tiff``, ``bmp``, ``heic``.
    input_image_formats: List[str]
    #: ``max_renditions``, ``max_width``, ``segment_seconds``, and ``image``
    #: (:class:`ImageLimits`).
    limits: Dict[str, Any]
    system_presets: List[Preset]
    #: The output spec (v2) as data: every field, when it is required, and
    #: what it takes. :func:`transcdr.validate_output` checks the same table.
    output: OutputCapabilities


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


# --------------------------------------------------------------------------
# Announcements: the changelog and service-credit notices
# --------------------------------------------------------------------------


class AnnouncementLink(TypedDict):
    """A call to action. A ``url`` that is a path (``/app/…``) is on the dashboard."""

    label: str
    url: str


class ServiceCredit(TypedDict, total=False):
    """What an incident's credit gave back to your organization."""

    incident_id: str
    amount_usd: float
    #: How many times the affected charges were credited.
    multiplier: int
    #: The affected jobs.
    jobs: List[str]
    applied_at: str


class Announcement(TypedDict, total=False):
    object: Literal["announcement"]
    id: str
    kind: Literal["changelog", "service_credit"]
    title: str
    #: Markdown.
    body: str
    #: When it was published.
    published_at: Optional[str]
    link: Optional[AnnouncementLink]
    #: Changelog entries only; may be empty.
    tags: List[str]
    #: Service credits only.
    credit: Optional[ServiceCredit]
    #: Always ``False`` for API keys, which have no user to remember it for.
    seen: bool
    seen_at: Optional[str]
