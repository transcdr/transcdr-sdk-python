"""Python client for the Transcdr video-transcoding API.

::

    from transcdr import Transcdr

    client = Transcdr()  # reads TRANSCDR_API_KEY
    asset = client.uploads.upload_file("keynote.mov")
    job = client.jobs.create(input=asset["id"], preset="hls-av1-abr")
    job = client.jobs.wait(job["id"])
"""

from . import types, webhooks
from ._base_client import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, NOT_GIVEN
from ._client import AsyncTranscdr, Transcdr
from ._errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    InvalidRequestError,
    NotFoundError,
    PermissionDeniedError,
    QuotaError,
    RateLimitError,
    SignatureVerificationError,
    TranscdrError,
    WaitTimeoutError,
)
from ._version import __version__
from .types import is_session
from .pagination import AsyncPage, SyncPage

__all__ = [
    "__version__",
    "Transcdr",
    "AsyncTranscdr",
    "SyncPage",
    "AsyncPage",
    "types",
    "webhooks",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "NOT_GIVEN",
    "is_session",
    "TranscdrError",
    "APIConnectionError",
    "APITimeoutError",
    "AuthenticationError",
    "PermissionDeniedError",
    "InvalidRequestError",
    "NotFoundError",
    "RateLimitError",
    "QuotaError",
    "APIError",
    "SignatureVerificationError",
    "WaitTimeoutError",
]
