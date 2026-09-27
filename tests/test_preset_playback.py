"""Preset categories and compatibility: where a preset is shown and where its
output plays."""

from __future__ import annotations

import json

import pytest

from transcdr import types

from .conftest import AsyncRecorder, Recorder, json_response

PRESET = {
    "object": "preset",
    "id": "web-av1-1080p",
    "slug": "web-av1-1080p",
    "name": "Web AV1 1080p",
    "system": True,
    "category": "web",
    "compatibility": ["web", "android", "smart_tv"],
    "compatibility_notes": {"web": "Chrome 70+", "android": "Android 10+", "smart_tv": "AV1 TVs"},
    "output": {},
}
PAGE = {"object": "list", "data": [PRESET], "has_more": False, "next_cursor": None}


def test_presets_carry_their_category_and_compatibility(make_client):
    rec = Recorder(json_response(200, PRESET))
    preset = make_client(rec).presets.retrieve("web-av1-1080p")
    assert preset["category"] == "web"
    assert preset["compatibility"] == ["web", "android", "smart_tv"]
    assert preset["compatibility_notes"]["android"] == "Android 10+"


def test_the_aliases_are_exported():
    assert "PresetCategory" in types.__all__
    assert "Platform" in types.__all__


@pytest.mark.parametrize(
    "kwargs,query",
    [
        ({"category": "web"}, {"category": "web"}),
        ({"category": ["web", "social"]}, {"category": "web,social"}),
        ({"compatible_with": "ios"}, {"compatible_with": "ios"}),
        ({"compatible_with": ["ios", "android"]}, {"compatible_with": "ios,android"}),
        ({}, {}),
    ],
)
def test_list_filters_join_lists_with_commas(make_client, kwargs, query):
    rec = Recorder(json_response(200, PAGE))
    make_client(rec).presets.list(**kwargs)
    params = dict(rec.requests[0].url.params)
    assert {k: v for k, v in params.items() if k in ("category", "compatible_with")} == query


def test_create_and_replace_send_the_organizations_own_values(make_client):
    rec = Recorder(json_response(201, PRESET), json_response(200, PRESET))
    client = make_client(rec)
    client.presets.create(
        name="Phones",
        output={"codec": "h265"},
        category="mobile",
        compatibility=["ios", "android"],
        compatibility_notes={"ios": "Our app only."},
    )
    client.presets.replace("pre_1", name="Phones", output={}, category="tv")
    created = json.loads(rec.requests[0].content)
    assert created["category"] == "mobile"
    assert created["compatibility"] == ["ios", "android"]
    assert created["compatibility_notes"] == {"ios": "Our app only."}
    replaced = json.loads(rec.requests[1].content)
    assert replaced["category"] == "tv"
    assert "compatibility" not in replaced


def test_update_sends_null_to_derive_again_and_leaves_out_what_is_not_given(make_client):
    rec = Recorder(json_response(200, PRESET), json_response(200, PRESET))
    client = make_client(rec)
    client.presets.update("pre_1", category=None, compatibility=None, compatibility_notes=None)
    client.presets.update("pre_1", compatibility=["smart_tv"])
    cleared = json.loads(rec.requests[0].content)
    assert cleared == {"category": None, "compatibility": None, "compatibility_notes": None}
    assert json.loads(rec.requests[1].content) == {"compatibility": ["smart_tv"]}


@pytest.mark.asyncio
async def test_async_list_and_update(make_async_client):
    rec = AsyncRecorder(json_response(200, PAGE), json_response(200, PRESET))
    client = make_async_client(rec)
    page = await client.presets.list(category=["web"], compatible_with=["web", "android"])
    assert page.data[0]["category"] == "web"
    params = rec.requests[0].url.params
    assert (params["category"], params["compatible_with"]) == ("web", "web,android")
    await client.presets.update("pre_1", category=None)
    assert json.loads(rec.requests[1].content) == {"category": None}
