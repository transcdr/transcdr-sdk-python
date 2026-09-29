# Changelog

## 1.0.0

Output spec v2. This release speaks v2 only; it is a breaking change for every spec you build or
read.

### Changed

- `OutputSpec` is declared in sections (`kind`, `container`, `video`, `audio`, `image`,
  `renditions`, `subtitles`, `trim`, `privacy`) and has no defaults: `VideoOutput | AudioOutput |
  ImageOutput`, whose always-required keys are required. Exclusive choices are unions
  (`VideoQuality | VideoCrf | VideoCbr`, `RenditionSizes | RenditionLadder | RenditionSourceSize`,
  `SubtitleTracks | SubtitleLanguages`, `PrivacyPreset | PrivacyFields`, `AudioTrack | AudioDrop`,
  and the `Gop`, `ImageFrames`, `FrameRate.max` and `Trim.end` forms). Values that follow the
  source are written out: `"source"`, `"standard"`, `"from_color"`, `"by_size"`, `"poster"`,
  `"segment"`, `"all"`.
- `jobs.create`, `presets.create`, `presets.replace` and `automations.create` check a whole spec
  sent without a preset and raise `InvalidRequestError` (code `validation_failed`, every failure in
  `errors`) without sending it. A job or automation needs a preset or a whole `output`.
- Preset overrides (`output` with a `preset`, and `presets.update`) are `OutputOverrides`:
  objects merge, lists replace, one choice of a group replaces the others, `None` removes a field.
- `FlacCompression` is `fast | balanced | best` (v1's `default` is `balanced`).
- Removed the v1 types `Mode`, `AudioMode`, `AudioContainer`, `Quality`, `Rendition`,
  `AudioSettings` and `OutputSpecInput`.

### Removed

- The platform operator console (`client.admin`, with its announcements and incidents, and the
  `AdminOverview`, `AdminJob`, `Incident` and `IncidentDetector` types). It was never usable with
  a customer's credentials, and it is not part of the public SDK.

### Added

- `transcdr.validate_output(spec)`: every missing field (by full path, with the condition that
  needs it), every field that does not apply and every exclusive group without exactly one choice,
  in the API's order and words.
- `TranscdrError.errors`: a 422's `error.errors`, every failure of a refused spec.
- `presets.versions(id)` and `presets.get_version(id, n)`; `Preset.version`; `preset="slug@N"`
  pins a version.
- `Job.preset`: `{id, slug, version, overrides}`, where the spec came from.
- `Automation.resolved_output`: the spec its preset and overrides resolve to now.
- `Capabilities.output`: the spec's fields, conditions, groups, containers, audio codecs and
  follow values, as data.
- `privacy` types: `PrivacyPreset` (a preset, refined by any categories given beside it),
  `PrivacyFields` (all four, no preset) and the category values.

### Migrating from v1

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
