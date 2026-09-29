from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx
import pytest

from transcdr import AsyncTranscdr, Transcdr

BASE_URL = "https://api.test"
API_KEY = "tdk_test_example"

Handler = Callable[[httpx.Request], httpx.Response]

#: Output specs and what the API says of them: the cases shared by every
#: SDK's copy of the required-field table.
OUTPUT_CASES: List[Dict[str, Any]] = json.loads(
    (Path(__file__).parent / "fixtures" / "output-validation-cases.json").read_text(encoding="utf-8")
)


def output_case(name: str) -> Dict[str, Any]:
    """A spec from the shared cases, by name (a fresh copy)."""
    for case in OUTPUT_CASES:
        if case["name"] == name:
            return json.loads(json.dumps(case["output"]))
    raise KeyError(name)


#: Complete v2 specs: the contract's examples.
HLS_CBR = output_case("hls cbr sizes")
SINGLE_MP4 = output_case("single mp4")
AUDIO_MP3 = output_case("audio mp3")
STILLS = output_case("image stills")


def json_response(status: int, body: Any, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
    return httpx.Response(
        status,
        content=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
    )


def error_body(type_: str, code: str, message: str, **extra: Any) -> Dict[str, Any]:
    return {"error": {"type": type_, "code": code, "message": message, **extra}}


class Recorder:
    """A MockTransport handler that records requests and replays queued responses."""

    def __init__(self, *responses: Any) -> None:
        self.responses: List[Any] = list(responses)
        self.requests: List[httpx.Request] = []
        self.bodies: List[bytes] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.bodies.append(request.read())
        if not self.responses:
            raise AssertionError(f"unexpected request {request.method} {request.url}")
        nxt = self.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        if callable(nxt):
            return nxt(request)
        return nxt

    def json(self, index: int = -1) -> Any:
        return json.loads(self.bodies[index])


class AsyncRecorder(Recorder):
    async def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.bodies.append(await request.aread())
        if not self.responses:
            raise AssertionError(f"unexpected request {request.method} {request.url}")
        nxt = self.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        if callable(nxt):
            return nxt(request)
        return nxt


@pytest.fixture
def sleeps() -> List[float]:
    return []


@pytest.fixture
def make_client(sleeps: List[float]) -> Callable[..., Transcdr]:
    clients: List[Transcdr] = []

    def factory(handler: Handler, **kwargs: Any) -> Transcdr:
        kwargs.setdefault("api_key", API_KEY)
        kwargs.setdefault("base_url", BASE_URL)
        client = Transcdr(http_client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs)
        client._sleep = sleeps.append  # type: ignore[method-assign]
        clients.append(client)
        return client

    return factory


@pytest.fixture
def make_async_client(sleeps: List[float]) -> Callable[..., AsyncTranscdr]:
    def factory(recorder: AsyncRecorder, **kwargs: Any) -> AsyncTranscdr:
        kwargs.setdefault("api_key", API_KEY)
        kwargs.setdefault("base_url", BASE_URL)
        client = AsyncTranscdr(
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(recorder.handle)), **kwargs
        )

        async def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        client._sleep = fake_sleep  # type: ignore[method-assign]
        return client

    return factory
