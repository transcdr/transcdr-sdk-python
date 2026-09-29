"""Checking an output spec before it is sent.

:func:`validate_output` checks a whole v2 spec against the same table the API
uses (:mod:`transcdr._output_rules`) and returns every problem at once, in
the API's order and words: missing fields first as each comes, fields that
do not apply, then exclusive groups with no choice or more than one. An
empty list means the spec has every field it needs and none it cannot have.
Values against each other (HDR colour with 8-bit, MP3 in HLS) and value
ranges are left to the API.

``jobs.create``, ``presets.create``, ``presets.replace`` and
``automations.create`` run it on a whole spec sent without a preset, and
raise :class:`~transcdr.InvalidRequestError` (``code="validation_failed"``,
``errors`` listing every failure) without sending the request.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Tuple

from ._errors import InvalidRequestError
from ._output_rules import FIELDS, GROUPS, Condition
from .types import FieldError

__all__ = ["validate_output", "check_output", "FIELDS", "GROUPS"]

def _lookup(document: Any, path: str) -> Any:
    at = document
    for key in path.split("."):
        if not isinstance(at, dict) or key not in at:
            return None
        at = at[key]
    return at


def _text(value: Any) -> Optional[str]:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _term_holds(document: Any, path: str, values: Sequence[str]) -> bool:
    found = _lookup(document, path)
    if tuple(values) == ("*",):
        return found is not None
    if tuple(values) == ("!",):
        return found is None
    if isinstance(found, list):
        return any(_text(item) in values for item in found if _text(item) is not None)
    if found is None:
        return False
    text = _text(found)
    return text is not None and text in values


def _holds(document: Any, condition: Condition) -> bool:
    return any(all(_term_holds(document, path, values) for path, values in clause) for clause in condition)


def _or_list(items: Sequence[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " or " + items[-1]


def _describe(condition: Condition) -> str:
    clauses = []
    for clause in condition:
        parts = []
        for path, values in clause:
            if tuple(values) == ("*",):
                parts.append(f"{path} is given")
            elif tuple(values) == ("!",):
                parts.append(f"{path} is not given")
            else:
                parts.append(f"{path} is {_or_list(values)}")
        clauses.append(" and ".join(parts))
    return ", or ".join(clauses)


def _instances(document: Any, path: str) -> Iterable[Tuple[str, Any]]:
    if "[]." not in path:
        return [(path, _lookup(document, path))]
    head, rest = path.split("[].", 1)
    items = _lookup(document, head)
    if not isinstance(items, list):
        return []
    return [
        (f"{head}.{i}.{rest}", _lookup(item, rest) if isinstance(item, dict) else None)
        for i, item in enumerate(items)
    ]


def _error(path: str, message: str) -> FieldError:
    return {"param": f"output.{path}" if path else "output", "message": message}


def validate_output(spec: Any) -> List[FieldError]:
    """Every way ``spec`` falls short of a complete v2 output spec, as
    ``[{"param": "output.audio.bitrate", "message": "..."}]``, in the order
    the API reports them. Empty when it is complete."""
    if not isinstance(spec, dict):
        return [_error("", "output must be an object.")]
    kind = spec.get("kind")
    if kind is None:
        return [_error("kind", "output.kind is required: video, audio or image.")]
    if kind not in ("video", "audio", "image"):
        return [_error("kind", "output.kind must be video, audio or image.")]

    errors: List[FieldError] = []
    privacy_missing = _lookup(spec, "privacy") is None
    if privacy_missing:
        errors.append(
            _error(
                "privacy",
                "output.privacy is required: give privacy.preset (strip_all, strip_location or keep_all), "
                "or all of location, capture_time, device and descriptive.",
            )
        )

    # A field that does not apply is reported once, not with each of its own.
    refused: List[str] = []
    for field_path, required, when, is_object, _group, allowed in FIELDS:
        if privacy_missing and field_path.startswith("privacy"):
            continue
        # Required only under ``when``; also allowed under ``allowed``.
        required_here = _holds(spec, when)
        applies = required_here or (allowed is not None and _holds(spec, allowed))
        for path, value in _instances(spec, field_path):
            if any(path.startswith(r + ".") for r in refused):
                continue
            if value is None and required_here and required and not is_object:
                errors.append(_error(path, f"output.{path} is required when {_describe(when)}."))
            elif value is not None and not applies:
                refused.append(path)
                errors.append(
                    _error(
                        path,
                        f"output.{path} does not apply here: it applies when {_describe(when)}. "
                        "Remove it (or set it to null).",
                    )
                )

    for _name, parent, members, when in GROUPS:
        if not _holds(spec, when):
            continue
        given = [m for m in members if _lookup(spec, m) is not None]
        names = [m.rsplit(".", 1)[-1] for m in members]
        if not given:
            errors.append(_error(parent, f"output.{parent} needs one of {_or_list(names)}."))
        elif len(given) > 1:
            errors.append(
                _error(
                    given[1],
                    f"output.{parent} takes one of {_or_list(names)}, not {' and '.join(given)}.",
                )
            )
    return errors


def check_output(spec: Any) -> None:
    """Raise :class:`~transcdr.InvalidRequestError` listing every failure of
    :func:`validate_output`, the first as its ``param`` and ``message``.
    ``None`` is refused: without a preset, a whole spec is required."""
    if spec is None:
        errors: List[FieldError] = [
            {"param": "output", "message": "output is required when no preset is given: send a whole spec."}
        ]
    else:
        errors = validate_output(spec)
    if errors:
        first = errors[0]
        raise InvalidRequestError(
            first["message"],
            type="invalid_request_error",
            code="validation_failed",
            param=first["param"],
            errors=[{"param": e["param"], "message": e["message"]} for e in errors],
        )
