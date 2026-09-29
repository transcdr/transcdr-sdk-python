"""The output spec's required-field table, as data.

A copy of the table the API checks a spec against (and describes under
``GET /v1/capabilities`` -> ``output.fields`` / ``output.groups``). Each field
is needed (or, when ``required`` is false, allowed) when any clause of
``when`` holds; a clause holds when each of its ``(path, values)`` terms
does. ``"*"`` means the path is present, ``"!"`` that it is absent. A field
with ``allowed`` may also be given when that holds, without being
required (the privacy categories beside a preset). Otherwise, outside
``when`` a field is refused. ``[]`` in a path stands for each entry of a list.
"""

from __future__ import annotations

from typing import Optional, Tuple

Term = Tuple[str, Tuple[str, ...]]
Condition = Tuple[Tuple[Term, ...], ...]
#: ``(path, required, when, object, group, allowed)``
Field = Tuple[str, bool, Condition, bool, Optional[str], Optional[Condition]]
#: ``(name, parent, members, when)``
Group = Tuple[str, str, Tuple[str, ...], Condition]

FIELDS: Tuple[Field, ...] = (
    ('kind', True, ((), ), False, None, None),
    ('container', True, ((('kind', ('video', 'audio',)), ), ), True, None, None),
    ('container.format', True, ((('kind', ('video', 'audio',)), ), ), False, None, None),
    ('container.segment_seconds', True, ((('kind', ('video',)), ('container.format', ('hls',)), ), ), False, None, None),
    ('video', True, ((('kind', ('video',)), ), ), True, None, None),
    ('video.codec', True, ((('kind', ('video',)), ), ), False, None, None),
    ('video.quality', False, ((('kind', ('video',)), ), ), False, 'video.rate', None),
    ('video.crf', False, ((('kind', ('video',)), ), ), False, 'video.rate', None),
    ('video.cbr', False, ((('kind', ('video',)), ), ), True, 'video.rate', None),
    ('video.cbr.bitrate', True, ((('kind', ('video',)), ('video.cbr', ('*',)), ), ), False, None, None),
    ('video.cbr.buffer_ms', True, ((('kind', ('video',)), ('video.cbr', ('*',)), ), ), False, None, None),
    ('video.bit_depth', True, ((('kind', ('video',)), ), ), False, None, None),
    ('video.color', True, ((('kind', ('video',)), ), ), False, None, None),
    ('video.frame_rate', True, ((('kind', ('video',)), ), ), True, None, None),
    ('video.frame_rate.max', True, ((('kind', ('video',)), ), ), False, None, None),
    ('video.gop', True, ((('kind', ('video',)), ), ), False, None, None),
    ('video.filters', True, ((('kind', ('video',)), ), ), False, None, None),
    ('audio', True, ((('kind', ('video', 'audio',)), ), ), True, None, None),
    ('audio.handling', True, ((('kind', ('video', 'audio',)), ), ), False, None, None),
    ('audio.codec', True, ((('kind', ('video', 'audio',)), ('audio.handling', ('auto', 'encode',)), ), ), False, None, None),
    ('audio.bitrate', True, ((('kind', ('video', 'audio',)), ('audio.handling', ('auto', 'encode',)), ('audio.codec', ('opus', 'mp3', 'aac',)), ), ), False, None, None),
    ('audio.channels', True, ((('kind', ('video', 'audio',)), ('audio.handling', ('auto', 'encode',)), ), ), False, None, None),
    ('audio.he_aac', True, ((('kind', ('video', 'audio',)), ('audio.handling', ('auto', 'encode',)), ), ), False, None, None),
    ('audio.stereo_fallback', True, ((('kind', ('video',)), ('container.format', ('hls',)), ('audio.handling', ('auto', 'encode',)), ), ), False, None, None),
    ('audio.bit_depth', True, ((('kind', ('video', 'audio',)), ('audio.handling', ('auto', 'encode',)), ('audio.codec', ('flac', 'alac',)), ), ), False, None, None),
    ('audio.flac_compression', True, ((('kind', ('video', 'audio',)), ('audio.handling', ('auto', 'encode',)), ('audio.codec', ('flac',)), ), ), False, None, None),
    ('image', True, ((('kind', ('image',)), ), ), True, None, None),
    ('image.formats', True, ((('kind', ('image',)), ), ), False, None, None),
    ('image.lossless', True, ((('kind', ('image',)), ('image.formats', ('webp',)), ), ), False, None, None),
    ('image.quality', True, ((('kind', ('image',)), ('image.formats', ('avif', 'jpeg',)), ), (('kind', ('image',)), ('image.formats', ('webp',)), ('image.lossless', ('false',)), ), ), False, None, None),
    ('image.color_profile', True, ((('kind', ('image',)), ), ), False, None, None),
    ('image.frames', True, ((('kind', ('image',)), ), ), False, None, None),
    ('renditions', True, ((('kind', ('video', 'image',)), ), ), True, None, None),
    ('renditions.sizes', False, ((('kind', ('video', 'image',)), ), ), False, 'renditions', None),
    ('renditions.ladder', False, ((('kind', ('video',)), ), ), True, 'renditions', None),
    ('renditions.source_size', False, ((('kind', ('video', 'image',)), ), ), True, 'renditions', None),
    ('renditions.sizes[].label', True, ((('kind', ('video', 'image',)), ('renditions.sizes', ('*',)), ), ), False, None, None),
    ('renditions.sizes[].width', True, ((('kind', ('video', 'image',)), ('renditions.sizes', ('*',)), ), ), False, None, None),
    ('renditions.sizes[].height', True, ((('kind', ('video', 'image',)), ('renditions.sizes', ('*',)), ), ), False, None, None),
    ('renditions.sizes[].fit', True, ((('kind', ('video', 'image',)), ('renditions.sizes', ('*',)), ), ), False, None, None),
    ('renditions.sizes[].orientation', True, ((('kind', ('video', 'image',)), ('renditions.sizes', ('*',)), ), ), False, None, None),
    ('renditions.sizes[].upscale', True, ((('kind', ('video', 'image',)), ('renditions.sizes', ('*',)), ), ), False, None, None),
    ('renditions.sizes[].video', False, ((('kind', ('video',)), ('video.cbr', ('*',)), ('renditions.sizes', ('*',)), ), ), False, None, None),
    ('renditions.ladder.max_short_side', True, ((('kind', ('video',)), ('renditions.ladder', ('*',)), ), ), False, None, None),
    ('renditions.ladder.fit', True, ((('kind', ('video',)), ('renditions.ladder', ('*',)), ), ), False, None, None),
    ('renditions.ladder.upscale', True, ((('kind', ('video',)), ('renditions.ladder', ('*',)), ), ), False, None, None),
    ('renditions.source_size.label', True, ((('kind', ('video', 'image',)), ('renditions.source_size', ('*',)), ), ), False, None, None),
    ('renditions.source_size.fit', True, ((('kind', ('video', 'image',)), ('renditions.source_size', ('*',)), ), ), False, None, None),
    ('renditions.source_size.upscale', True, ((('kind', ('video', 'image',)), ('renditions.source_size', ('*',)), ), ), False, None, None),
    ('subtitles', True, ((('kind', ('video',)), ), ), True, None, None),
    ('subtitles.tracks', False, ((('kind', ('video',)), ), ), False, 'subtitles', None),
    ('subtitles.languages', False, ((('kind', ('video',)), ), ), False, 'subtitles', None),
    ('trim', True, ((('kind', ('video',)), ), ), True, None, None),
    ('trim.start', True, ((('kind', ('video',)), ), ), False, None, None),
    ('trim.end', True, ((('kind', ('video',)), ), ), False, None, None),
    ('privacy', True, ((), ), True, None, None),
    ('privacy.preset', False, ((), ), False, None, None),
    ('privacy.location', True, ((('privacy.preset', ('!',)), ), ), False, None, ((), )),
    ('privacy.capture_time', True, ((('privacy.preset', ('!',)), ), ), False, None, ((), )),
    ('privacy.device', True, ((('privacy.preset', ('!',)), ), ), False, None, ((), )),
    ('privacy.descriptive', True, ((('privacy.preset', ('!',)), ), ), False, None, ((), )),
)

GROUPS: Tuple[Group, ...] = (
    ('video.rate', 'video', ('video.quality', 'video.crf', 'video.cbr',), ((('kind', ('video',)), ), )),
    ('renditions', 'renditions', ('renditions.sizes', 'renditions.ladder', 'renditions.source_size',), ((('kind', ('video', 'image',)), ), )),
    ('subtitles', 'subtitles', ('subtitles.tracks', 'subtitles.languages',), ((('kind', ('video',)), ), )),
)
