"""Output spec v2: the required-field check (the cases every SDK shares),
refusing an incomplete spec before it is sent, preset versions, provenance,
automations' resolved spec and ``capabilities.output``."""

from __future__ import annotations

import json

import pytest

from transcdr import InvalidRequestError, validate_output
from transcdr._output_rules import FIELDS, GROUPS

from .conftest import (
    AUDIO_MP3,
    HLS_CBR,
    OUTPUT_CASES,
    SINGLE_MP4,
    STILLS,
    AsyncRecorder,
    Recorder,
    error_body,
    json_response,
)


@pytest.mark.parametrize("case", OUTPUT_CASES, ids=[c["name"] for c in OUTPUT_CASES])
def test_validate_output_matches_the_api(case):
    assert validate_output(case["output"]) == case["errors"]


def test_the_table_names_every_group_member():
    paths = {f[0] for f in FIELDS}
    for _name, parent, members, _when in GROUPS:
        assert parent in paths
        assert set(members) <= paths


def test_every_missing_path_at_once():
    spec = {k: v for k, v in SINGLE_MP4.items() if k != "privacy"}
    spec["audio"] = {"handling": "encode", "codec": "aac", "channels": "source", "he_aac": "auto"}
    spec["video"] = {k: v for k, v in spec["video"].items() if k != "frame_rate"}
    assert [e["param"] for e in validate_output(spec)] == [
        "output.privacy",
        "output.video.frame_rate.max",
        "output.audio.bitrate",
    ]


def test_an_incomplete_spec_is_refused_before_it_is_sent(make_client):
    rec = Recorder()
    client = make_client(rec)
    with pytest.raises(InvalidRequestError) as info:
        client.jobs.create(input="ast_1", output={"kind": "audio", "container": {"format": "mp3"}})
    err = info.value
    assert err.code == "validation_failed"
    assert err.status is None
    assert err.param == "output.privacy"
    assert [e["param"] for e in err.errors] == ["output.privacy", "output.audio.handling"]
    assert rec.requests == []


def test_a_job_needs_a_preset_or_a_whole_spec(make_client):
    rec = Recorder()
    with pytest.raises(InvalidRequestError) as info:
        make_client(rec).jobs.create(input="ast_1")
    assert info.value.param == "output"
    assert rec.requests == []


def test_v1_output_is_not_sent(make_client):
    rec = Recorder()
    with pytest.raises(InvalidRequestError) as info:
        make_client(rec).jobs.create(input="ast_1", output={"mode": "single", "codec": "av1"})
    assert info.value.param == "output.kind"
    assert rec.requests == []


def test_preset_overrides_are_sent_unchecked(make_client):
    returned = {
        "object": "job",
        "id": "job_1",
        "preset_id": "social-vertical-1080x1920",
        "preset": {"id": "social-vertical-1080x1920", "version": 1,
                   "overrides": {"video": {"frame_rate": {"max": 24}}}},
        "output": SINGLE_MP4,
    }  # fmt: skip
    rec = Recorder(json_response(201, returned))
    job = make_client(rec).jobs.create(
        input="ast_1",
        preset="social-vertical-1080x1920",
        output={"video": {"frame_rate": {"max": 24}}, "container": {"segment_seconds": None}},
    )
    assert rec.json() == {
        "input": {"type": "asset", "asset_id": "ast_1"},
        "preset": "social-vertical-1080x1920",
        "output": {"video": {"frame_rate": {"max": 24}}, "container": {"segment_seconds": None}},
    }
    assert job["preset"]["version"] == 1
    assert job["preset"]["overrides"] == {"video": {"frame_rate": {"max": 24}}}
    assert job["output"]["kind"] == "video"


def test_presets_create_and_replace_check_the_spec(make_client):
    rec = Recorder()
    client = make_client(rec)
    with pytest.raises(InvalidRequestError):
        client.presets.create(name="Mine", output={"kind": "image"})
    with pytest.raises(InvalidRequestError):
        client.presets.replace("pre_1", name="Mine", output={"kind": "video"})
    assert rec.requests == []


def test_preset_update_merges_a_partial(make_client):
    rec = Recorder(json_response(200, {"object": "preset", "id": "pre_1", "version": 3, "output": HLS_CBR}))
    preset = make_client(rec).presets.update("pre_1", output={"video": {"crf": 23}})
    assert rec.json() == {"output": {"video": {"crf": 23}}}
    assert preset["version"] == 3


def test_preset_versions(make_client):
    version = {"object": "preset_version", "version": 1, "output": STILLS, "created_at": None}
    rec = Recorder(
        json_response(200, {"object": "list", "data": [version], "has_more": False}),
        json_response(200, {"object": "preset", "id": "web-avif", "slug": "web-avif", "version": 1,
                            "output": STILLS}),  # fmt: skip
    )
    client = make_client(rec)
    versions = client.presets.versions("web-avif")
    assert versions.data[0]["version"] == 1
    assert versions.data[0]["output"]["kind"] == "image"
    preset = client.presets.get_version("web-avif", 1)
    assert preset["version"] == 1
    assert [r.url.raw_path for r in rec.requests] == [b"/v1/presets/web-avif/versions", b"/v1/presets/web-avif@1"]


def test_automation_overrides_and_resolved_output(make_client):
    automation = {
        "object": "automation",
        "id": "aut_1",
        "preset": "podcast-mp3@1",
        "output": {"audio": {"bitrate": "96k"}},
        "resolved_output": {**AUDIO_MP3, "audio": {**AUDIO_MP3["audio"], "bitrate": "96k"}},
    }
    rec = Recorder(json_response(201, automation))
    made = make_client(rec).automations.create(
        name="Podcasts", source={"connection_id": "con_1"}, preset="podcast-mp3@1",
        output={"audio": {"bitrate": "96k"}},
    )  # fmt: skip
    assert rec.json()["output"] == {"audio": {"bitrate": "96k"}}
    assert made["resolved_output"]["audio"]["bitrate"] == "96k"


def test_an_automation_without_a_preset_needs_a_whole_spec(make_client):
    rec = Recorder()
    with pytest.raises(InvalidRequestError):
        make_client(rec).automations.create(name="a", source={"connection_id": "con_1"})
    assert rec.requests == []


def test_capabilities_output(make_client):
    caps = {
        "object": "capabilities",
        "output": {
            "version": 2,
            "kinds": ["video", "audio", "image"],
            "fields": [
                {"path": "container.segment_seconds", "required": True,
                 "when": [{"kind": ["video"], "container.format": ["hls"]}],
                 "shape": {"type": "number", "min": 1, "max": 20}, "group": None, "description": "Seconds per HLS segment."},
            ],
            "groups": [{"name": "video.rate", "members": ["video.quality", "video.crf", "video.cbr"],
                        "when": [{"kind": ["video"]}], "exactly_one": True}],
            "conditions": "…",
            "containers": [{"id": "mp3", "kind": "audio", "audio_codecs": ["mp3"]}],
            "audio_codecs": [{"id": "mp3", "name": "MP3", "lossless": False, "max_channels": 2,
                              "bitrates": ["32k", "320k"]}],
            "follow_values": {"trim.end: source": "the end of the source"},
            "compatibility": {"v1_requests": "accepted",
                              "v1_responses": {"header": "Transcdr-Output-Spec", "value": "v1",
                                               "query": "output_spec=v1 (GET)",
                                               "sunset": "Wed, 31 Mar 2027 00:00:00 GMT"}},
        },
    }  # fmt: skip
    rec = Recorder(json_response(200, caps))
    output = make_client(rec).capabilities.retrieve()["output"]
    assert output["version"] == 2
    assert output["fields"][0]["when"] == [{"kind": ["video"], "container.format": ["hls"]}]
    assert output["groups"][0]["exactly_one"] is True
    assert output["compatibility"]["v1_responses"]["header"] == "Transcdr-Output-Spec"


def test_the_sdk_sends_no_compatibility_header(make_client):
    rec = Recorder(json_response(200, {"object": "job", "id": "job_1", "output": SINGLE_MP4}))
    make_client(rec).jobs.retrieve("job_1")
    assert "Transcdr-Output-Spec" not in rec.requests[0].headers
    assert "output_spec" not in rec.requests[0].url.params


def test_a_422_carries_every_error(make_client):
    errors = [
        {"param": "output.audio.bitrate", "message": "output.audio.bitrate is required when …"},
        {"param": "output.privacy", "message": "output.privacy is required: …"},
    ]
    body = error_body("invalid_request_error", "validation_failed", errors[0]["message"],
                      param=errors[0]["param"], errors=errors)  # fmt: skip
    rec = Recorder(json_response(422, body))
    with pytest.raises(InvalidRequestError) as info:
        make_client(rec).jobs.create(input="ast_1", preset="podcast-mp3", output={"audio": {"bitrate": None}})
    assert info.value.errors == errors
    assert json.loads(rec.bodies[0])["output"] == {"audio": {"bitrate": None}}


@pytest.mark.asyncio
async def test_async_checks_and_versions(make_async_client):
    rec = AsyncRecorder(json_response(200, {"object": "list", "data": [], "has_more": False}))
    client = make_async_client(rec)
    with pytest.raises(InvalidRequestError):
        await client.jobs.create(input="ast_1", output={"kind": "video"})
    with pytest.raises(InvalidRequestError):
        await client.presets.create(name="x", output={})
    await client.presets.versions("pre_1")
    assert [r.url.path for r in rec.requests] == ["/v1/presets/pre_1/versions"]
