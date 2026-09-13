"""Offline-only CC-BY OER curriculum-outline adapter.

The adapter intentionally extracts curriculum metadata only.  It never reads
lesson body prose, exercises, or media markup, and it performs no I/O beyond
the checked-in snapshot path passed to :func:`parse`.
"""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from api.services.content_etl.registry import SourceRegistryError, validate_source_url


ADAPTER_VERSION = 1
SNAPSHOT_SCHEMA_VERSION = 1
SOURCE_NAME = "oer_curriculum"
LICENSE_ID = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MARKUP = re.compile(r"[<>]")
_FIELD_NAMES = {
    "outcome",
    "topic",
    "grammar_scope",
    "vocabulary_scope",
}
_HTML_CHECKSUM_META = re.compile(
    rb"<meta\\b(?=[^>]*\\bname\\s*=\\s*[\"']oer:raw-checksum[\"'])[^>]*>",
    re.IGNORECASE,
)


_HTML_CHECKSUM_META_CANONICAL = re.compile(
    rb"<meta\b(?=[^>]*\bname\s*=\s*[\"']oer:raw-checksum[\"'])[^>]*>",
    re.IGNORECASE,
)

MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024
MAX_RECORDS = 10_000
MAX_TEXT_LENGTH = 5_000
MAX_SCOPE_ITEMS = 100


def _sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _plain_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"{field} must not be empty")
    if _CONTROL_CHARS.search(cleaned) or _MARKUP.search(cleaned):
        raise ValueError(f"{field} must be plain text without markup")
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise ValueError(f"{field} exceeds maximum length of {MAX_TEXT_LENGTH}")
    return cleaned


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _plain_text(value, field)


def _scope(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list):
        raise ValueError(f"{field} must be a string or list of strings")
    if len(values) > MAX_SCOPE_ITEMS:
        raise ValueError(f"{field} exceeds maximum item count of {MAX_SCOPE_ITEMS}")
    return list(dict.fromkeys(_plain_text(item, field) for item in values))


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug[:80] or _sha256(value)[:16]


def _identity(*parts: str) -> str:
    return f"{SOURCE_NAME}:{_sha256('|'.join(parts))[:24]}"


def _declared_snapshot_checksum(payload: dict[str, Any], raw_bytes: bytes) -> str:
    """Hash the immutable snapshot excluding its checksum declaration.

    A checksum embedded in the file cannot hash the literal file bytes without
    being self-referential. JSON is canonicalized without ``raw_checksum``;
    HTML removes only the dedicated metadata tag, preserving all curriculum
    content (including intentionally ignored third-party media) in the hash.
    """
    if raw_bytes.lstrip().startswith(b"<"):
        return _sha256(_HTML_CHECKSUM_META_CANONICAL.sub(b"", raw_bytes))
    without_checksum = json.loads(raw_bytes.decode("utf-8"))
    if isinstance(without_checksum.get("source"), dict):
        without_checksum["source"] = dict(without_checksum["source"])
        without_checksum["source"].pop("raw_checksum", None)
    else:
        without_checksum.pop("raw_checksum", None)
    return _sha256(
        json.dumps(
            without_checksum,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def _validate_snapshot_metadata(payload: dict[str, Any], raw_bytes: bytes) -> dict[str, str]:
    if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("snapshot schema_version must be 1")
    metadata = payload.get("source") if isinstance(payload.get("source"), dict) else payload
    required = (
        "source_version",
        "source_url",
        "license_id",
        "license_url",
        "attribution_text",
        "raw_checksum",
    )
    missing = [field for field in required if not metadata.get(field)]
    if missing:
        raise ValueError("snapshot is missing required provenance: " + ", ".join(missing))
    if metadata["license_id"] != LICENSE_ID:
        raise ValueError("OER curriculum snapshots require CC-BY-4.0")
    if metadata["license_url"] != LICENSE_URL:
        raise ValueError("OER curriculum snapshots require the CC-BY 4.0 license URL")
    if metadata["raw_checksum"] != _declared_snapshot_checksum(payload, raw_bytes):
        raise ValueError("snapshot raw_checksum does not match checked-in file")
    source_url = str(metadata["source_url"])
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("source_url must be a credential-free HTTPS provenance URL")
    if parsed.query or parsed.fragment:
        raise ValueError("source_url must not include a query string or fragment")
    try:
        validate_source_url(SOURCE_NAME, source_url)
    except SourceRegistryError as exc:
        raise ValueError(str(exc)) from exc
    return {
        "source_version": _plain_text(metadata["source_version"], "source_version"),
        "source_url": source_url,
        "license_id": LICENSE_ID,
        "license_url": LICENSE_URL,
        "attribution_text": _plain_text(metadata["attribution_text"], "attribution_text"),
        "raw_checksum": str(metadata["raw_checksum"]),
    }


class _OutlineHTMLParser(HTMLParser):
    """Extract only headings and explicit ``data-oer-*`` outline metadata."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.course: dict[str, Any] = {"units": []}
        self._unit: dict[str, Any] | None = None
        self._lesson: dict[str, Any] | None = None
        self._heading_level: int | None = None
        self._heading_attrs: dict[str, str] = {}
        self._heading_text: list[str] = []
        self._excluded_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value or "" for key, value in attrs}
        if tag == "meta" and values.get("name", "").startswith("oer:"):
            self.meta[values["name"][4:].replace("-", "_")] = values.get("content", "")
        if tag in {"script", "iframe", "audio", "video", "img", "image", "object", "embed"}:
            self._excluded_depth += 1
        if tag in {"h1", "h2", "h3"}:
            self._heading_level = int(tag[1])
            self._heading_attrs = values
            self._heading_text = []

    def handle_data(self, data: str) -> None:
        # Script, iframe, audio, image, and arbitrary prose are never active
        # heading data and therefore never enter normalized records.
        if self._heading_level is not None and self._excluded_depth == 0:
            self._heading_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "iframe", "audio", "video", "img", "image", "object", "embed"}:
            self._excluded_depth = max(0, self._excluded_depth - 1)
        if self._heading_level != (int(tag[1]) if tag in {"h1", "h2", "h3"} else None):
            return
        title = " ".join("".join(self._heading_text).split())
        attrs = self._heading_attrs
        if title:
            fields = {
                field: attrs.get(f"data-oer-{field.replace('_', '-')}")
                for field in _FIELD_NAMES
                if attrs.get(f"data-oer-{field.replace('_', '-')}")
            }
            if self._heading_level == 1:
                self.course["title"] = title
                self.course.update(fields)
            elif self._heading_level == 2:
                self._unit = {"title": title, "lessons": [], **fields}
                self.course["units"].append(self._unit)
            elif self._heading_level == 3:
                if self._unit is None:
                    raise ValueError("lesson heading appears before a unit heading")
                self._lesson = {"title": title, **fields}
                self._unit["lessons"].append(self._lesson)
        self._heading_level = None
        self._heading_attrs = {}
        self._heading_text = []


def _html_snapshot(raw_bytes: bytes) -> dict[str, Any]:
    parser = _OutlineHTMLParser()
    try:
        parser.feed(raw_bytes.decode("utf-8"))
        parser.close()
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("OER curriculum snapshot must be UTF-8 JSON or HTML") from exc
    return {"schema_version": 1, "source": parser.meta, "curriculum": parser.course}


def _records(payload: dict[str, Any], raw_path: Path) -> list[dict[str, Any]]:
    curriculum = payload.get("curriculum", payload.get("course"))
    if not isinstance(curriculum, dict):
        raise ValueError("snapshot must contain a structured curriculum outline")
    course_title = _plain_text(curriculum.get("title"), "course.title")
    units = curriculum.get("units")
    if not isinstance(units, list) or not units:
        raise ValueError("curriculum.units must be a non-empty list")

    records: list[dict[str, Any]] = []

    def add(record_type: str, location: list[str], values: dict[str, Any]) -> None:
        if len(records) >= MAX_RECORDS:
            raise ValueError(f"curriculum exceeds maximum record count of {MAX_RECORDS}")
        outcome = _optional_text(values.get("outcome"), f"{record_type}.outcome")
        topics = _scope(values.get("topic"), f"{record_type}.topic")
        grammar = _scope(values.get("grammar_scope"), f"{record_type}.grammar_scope")
        vocabulary = _scope(values.get("vocabulary_scope"), f"{record_type}.vocabulary_scope")
        title = _plain_text(values.get("title"), f"{record_type}.title")
        stable_location = " / ".join(location)
        topic_ids = [f"curriculum:{record_type}:{_slug(stable_location)}"]
        topic_ids.extend(f"topic:{_slug(topic)}" for topic in topics)
        records.append(
            {
                "record_id": _identity(record_type, *location),
                "source_name": SOURCE_NAME,
                "source_version": payload["_metadata"]["source_version"],
                "source_record_id": f"{record_type}:{_slug(stable_location)}",
                "source_url": payload["_metadata"]["source_url"],
                "language": "en",
                "content_usage": "topic",
                "topic_ids": list(dict.fromkeys(topic_ids)),
                "lineage": {
                    "adapter": SOURCE_NAME,
                    "adapter_version": ADAPTER_VERSION,
                    "raw_path": raw_path.name,
                    "source_location": "/".join(location),
                },
                "attribution_text": payload["_metadata"]["attribution_text"],
                "license_id": LICENSE_ID,
                "license_url": LICENSE_URL,
                "raw_checksum": payload["_metadata"]["raw_checksum"],
                "metadata": {
                    "record_type": record_type,
                    "course_title": course_title,
                    "unit_title": location[1] if len(location) > 1 else None,
                    "lesson_title": title if record_type == "lesson" else None,
                    "title": title,
                    "outcome": outcome,
                    "topic": topics,
                    "grammar_scope": grammar,
                    "vocabulary_scope": vocabulary,
                },
            }
        )

    add("course", [course_title], curriculum)
    for unit in units:
        if not isinstance(unit, dict):
            raise ValueError("curriculum.units entries must be objects")
        unit_title = _plain_text(unit.get("title"), "unit.title")
        add("unit", [course_title, unit_title], unit)
        lessons = unit.get("lessons")
        if not isinstance(lessons, list) or not lessons:
            raise ValueError("unit.lessons must be a non-empty list")
        for lesson in lessons:
            if not isinstance(lesson, dict):
                raise ValueError("unit.lessons entries must be objects")
            lesson_title = _plain_text(lesson.get("title"), "lesson.title")
            add("lesson", [course_title, unit_title, lesson_title], lesson)
    return records


def parse(raw_path: Path) -> list[dict[str, Any]]:
    """Parse one checksummed local JSON or HTML curriculum outline snapshot."""
    try:
        size = raw_path.stat().st_size
    except OSError as exc:
        raise ValueError("OER curriculum snapshot could not be read") from exc
    if size > MAX_SNAPSHOT_BYTES:
        raise ValueError(
            f"OER curriculum snapshot exceeds maximum size of {MAX_SNAPSHOT_BYTES} bytes"
        )
    try:
        raw_bytes = raw_path.read_bytes()
    except OSError as exc:
        raise ValueError("OER curriculum snapshot could not be read") from exc
    if raw_path.suffix.casefold() in {".html", ".htm"}:
        payload = _html_snapshot(raw_bytes)
    else:
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
            raise ValueError("OER curriculum snapshot must be UTF-8 JSON or HTML") from exc
    if not isinstance(payload, dict):
        raise ValueError("OER curriculum snapshot root must be an object")
    payload = dict(payload)
    payload["_metadata"] = _validate_snapshot_metadata(payload, raw_bytes)
    return _records(payload, raw_path)


class OERCurriculumAdapter:
    source_name: str = SOURCE_NAME
    adapter_version: int = ADAPTER_VERSION

    def parse(self, raw_path: Path) -> list[dict[str, Any]]:
        return parse(raw_path)
