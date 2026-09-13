"""Build the original, offline English A1 Everyday Communication artifact.

The lexical input is intentionally limited to source-record-v2-derived data.  This
builder never treats an approved lexical source as the author of blueprint prose.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
DEFAULT_BLUEPRINT = HERE.parents[1] / "data" / "approved" / "a1-everyday-communication" / "curriculum-blueprint-v1.json"
DEFAULT_LEXICAL = DEFAULT_BLUEPRINT.with_name("lexical-records-v1.json")
SOURCES = {
    "oewn": {"source_version": "2025", "snapshot_id": "oewn:2025:9ca6d1dcb75f822fdd66617f7d9da48142ace38dd544d6ad5e2feca1674ad3fe", "raw_checksum": "9ca6d1dcb75f822fdd66617f7d9da48142ace38dd544d6ad5e2feca1674ad3fe", "license_id": "CC-BY-4.0", "official_url": "https://en-word.net/static/english-wordnet-2025.xml.gz", "usage": "lexical"},
    "cmudict": {"source_version": "74790861f652b15e4ac49015a90074ad62a27690", "snapshot_id": "cmudict:74790861f652b15e4ac49015a90074ad62a27690:81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22", "raw_checksum": "81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22", "license_id": "LicenseRef-CMUdict", "official_url": "https://github.com/cmusphinx/cmudict", "usage": "pronunciation"},
    "cefr_j": {"source_version": "d4e45b75b38f27b30dfc5c44d8c571aec7e7092f", "snapshot_id": "cefr-j:d4e45b75b38f27b30dfc5c44d8c571aec7e7092f:b0dd3c635f1c9a4fdf1490c7e5b7c48e8bbe55b652ad0c9860a95f98e10ae498", "raw_checksum": "b0dd3c635f1c9a4fdf1490c7e5b7c48e8bbe55b652ad0c9860a95f98e10ae498", "license_id": "LicenseRef-CEFR-J-Commercial", "official_url": "https://github.com/openlanguageprofiles/olp-en-cefrj", "usage": "lexical"},
}
SHA_FIELDS = ("raw_checksum", "normalized_sha256", "record_checksum_root")
MANIFEST_FIELDS = {"snapshot_id", "source_name", "source_version", "official_url", "license_id", "license_url", "attribution_text", "retrieved_at", "raw_checksum", "normalized_sha256", "normalized_bytes", "record_checksum_root", "adapter_version", "record_count"}

class BuildError(ValueError):
    pass

def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"{label} is not readable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise BuildError(f"{label} root must be an object")
    return value

def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BuildError("required text value is missing")
    return value.strip()

def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)

def _blueprint_words(blueprint: dict[str, Any]) -> list[dict[str, Any]]:
    course, units = blueprint.get("course"), blueprint.get("units")
    if blueprint.get("schema_version") != 1 or not isinstance(course, dict) or course.get("title") != "English A1 — Everyday Communication":
        raise BuildError("blueprint is not the approved English A1 curriculum blueprint")
    if not isinstance(units, list) or len(units) != 3:
        raise BuildError("blueprint must contain exactly three units")
    expected = (("greetings", "introductions", "personal-information"), ("daily-routine", "time-schedule", "home-work"), ("food", "shopping", "making-plans"))
    all_lessons: list[dict[str, Any]] = []
    for unit_index, (unit, slugs) in enumerate(zip(units, expected)):
        if not isinstance(unit, dict) or unit.get("order_index") != unit_index or not isinstance(unit.get("lessons"), list) or tuple(item.get("slug") for item in unit["lessons"] if isinstance(item, dict)) != slugs:
            raise BuildError("blueprint unit/lesson order or slugs are not approved")
        all_lessons.extend(unit["lessons"])
    if len(all_lessons) != 9:
        raise BuildError("blueprint must contain exactly nine lessons")
    words: list[dict[str, Any]] = []
    for lesson in all_lessons:
        required = ("title", "title_vi", "outcome", "outcome_vi", "description", "description_vi", "vocabulary", "exercises")
        if any(not _text(lesson.get(key)) for key in required[:6]) or len(lesson["vocabulary"]) != 10 or len(lesson["exercises"]) != 10:
            raise BuildError(f"lesson {lesson.get('slug')!r} lacks its original required content")
        ids = [exercise.get("id") for exercise in lesson["exercises"] if isinstance(exercise, dict)]
        if len(ids) != 10 or len(set(ids)) != 10:
            raise BuildError(f"lesson {lesson['slug']} exercise IDs are invalid")
        for word in lesson["vocabulary"]:
            if not isinstance(word, dict) or any(not _text(word.get(key)) for key in ("word", "definition", "translation_vi", "example", "part_of_speech")):
                raise BuildError(f"lesson {lesson['slug']} has invalid original vocabulary content")
            words.append(word)
    if len(words) != 90 or len({_text(word["word"]).casefold() for word in words}) != 90:
        raise BuildError("blueprint must contain 90 unique vocabulary words")
    return words

def _validate_input(payload: dict[str, Any], blueprint_words: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if set(payload) != {"schema_version", "records", "source_manifest"} or payload.get("schema_version") != 1:
        raise BuildError("lexical input must be lexical-records-v1 with schema_version, records, and source_manifest only")
    records, manifests = payload.get("records"), payload.get("source_manifest")
    if not isinstance(records, list) or len(records) != 90 or not isinstance(manifests, list) or len(manifests) != 3:
        raise BuildError("lexical input must contain exactly 90 records and three source manifests")
    manifest_by_source: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
            raise BuildError("lexical source manifest shape is invalid")
        source = _text(manifest.get("source_name"))
        if source not in SOURCES or source in manifest_by_source:
            raise BuildError("lexical source manifest has an unapproved or duplicate source")
        approved = SOURCES[source]
        if any(manifest.get(key) != approved[key] for key in ("source_version", "snapshot_id", "raw_checksum", "license_id", "official_url")):
            raise BuildError(f"{source} manifest is not the exact approved source pin")
        if any(not _is_sha(manifest.get(key)) for key in SHA_FIELDS) or not isinstance(manifest.get("normalized_bytes"), int) or manifest["normalized_bytes"] < 1 or not isinstance(manifest.get("record_count"), int) or manifest["record_count"] < 1 or not isinstance(manifest.get("adapter_version"), int) or manifest["adapter_version"] < 1:
            raise BuildError(f"{source} manifest has invalid integrity fields")
        _text(manifest.get("license_url")); _text(manifest.get("attribution_text")); _text(manifest.get("retrieved_at"))
        manifest_by_source[source] = manifest
    if set(manifest_by_source) != set(SOURCES):
        raise BuildError("lexical source manifests must be exactly OEWN, CMUdict, and CEFR-J")
    by_word: dict[str, dict[str, Any]] = {}
    for record_index, record in enumerate(records):
        if not isinstance(record, dict):
            raise BuildError("lexical record must be an object")
        required = ("id", "lesson_slug", "word", "cefr_level", "cefr_source_locator", "definition", "part_of_speech", "oewn_source_locator", "arpabet", "cmudict_source_locator", "enrichments", "provenance")
        if any(key not in record for key in required):
            raise BuildError("lexical record is missing verified fields")
        if record.get("cefr_level") != "A1" or not isinstance(record.get("enrichments"), dict) or not isinstance(record.get("provenance"), dict):
            raise BuildError("lexical record enrichment shape is invalid")
        for source, locator_key in (("cefr_j", "cefr_source_locator"), ("oewn", "oewn_source_locator"), ("cmudict", "cmudict_source_locator")):
            enrichment, provenance = record["enrichments"].get(source), record["provenance"].get(source)
            if not isinstance(enrichment, dict) or enrichment.get("matched") is not True or not _text(record.get(locator_key)):
                raise BuildError("lexical record is missing a verified source locator")
            if not isinstance(provenance, dict) or provenance.get("raw_checksum") != manifest_by_source[source]["raw_checksum"] or provenance.get("source_locator") != record[locator_key]:
                raise BuildError(f"lexical record provenance does not match the {source} manifest")
        word = _text(record["word"]).casefold()
        if word in by_word:
            raise BuildError(f"duplicate lexical record for {word!r}")
        record["_artifact_source"] = tuple(SOURCES)[record_index % len(SOURCES)]
        by_word[word] = record
    expected_words = {_text(item["word"]).casefold() for item in blueprint_words}
    if set(by_word) != expected_words:
        raise BuildError("lexical records must match the blueprint's exact 90-word vocabulary")
    if any(manifest_by_source[source]["record_count"] != len(records) for source in SOURCES):
        raise BuildError("lexical manifest record_count does not match its records")
    return by_word

def _vocabulary_item(original: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    source = record["_artifact_source"]
    pin = record["provenance"][source]
    locator = record[{"cefr_j": "cefr_source_locator", "oewn": "oewn_source_locator", "cmudict": "cmudict_source_locator"}[source]]
    lineage = {"adapter": "a1-verified-lexical-pack", "adapter_version": 1, "raw_path": f"{record['lesson_slug']}/{record['word']}", "source_location": locator, "lexilingo_original_fields": ["definition", "translation_vi", "example"]}
    checksum = _sha(record)
    return {"word": original["word"], "definition": original["definition"], "translation_vi": original["translation_vi"], "example": original["example"], "pronunciation": record.get("pronunciation"), "audio_url": None, "part_of_speech": original["part_of_speech"], "difficulty_level": "A1", "topic": "everyday_communication", "source_name": source, "source_url": SOURCES[source]["official_url"], "license_mode": "approved_dataset", "source_checksum": checksum, "source_version": pin["source_version"], "source_record_id": locator, "license_id": pin["license_id"], "license_url": {"oewn": "https://creativecommons.org/licenses/by/4.0/", "cmudict": "https://cmusphinx.github.io/cmudict/", "cefr_j": "https://github.com/openlanguageprofiles/olp-en-cefrj"}[source], "attribution_text": {"oewn": "Open English WordNet 2025", "cmudict": "Carnegie Mellon Pronouncing Dictionary", "cefr_j": "The CEFR-J Wordlist Version 1.5, compiled by Yukio Tono, Tokyo University of Foreign Studies"}[source], "raw_checksum": pin["raw_checksum"], "record_checksum": checksum, "lineage": lineage, "content_usage": SOURCES[source]["usage"]}

def build(blueprint: dict[str, Any], lexical: dict[str, Any]) -> dict[str, Any]:
    words = _blueprint_words(blueprint)
    records = _validate_input(lexical, words)
    course = blueprint["course"]
    units = []
    for unit in blueprint["units"]:
        lessons = []
        for lesson in unit["lessons"]:
            lessons.append({"title": lesson["title"], "description": lesson["description"], "order_index": lesson["order_index"], "vocabulary": [_vocabulary_item(item, records[item["word"].casefold()]) for item in lesson["vocabulary"]], "exercises": lesson["exercises"], "estimated_minutes": lesson["estimated_minutes"], "xp_reward": lesson["xp_reward"]})
        units.append({"title": unit["title"], "description": f"{unit['title_vi']}. Original LexiLingo curriculum.", "order_index": unit["order_index"], "lessons": lessons})
    manifest = sorted(lexical["source_manifest"], key=lambda item: item["source_name"])
    artifact = {"schema_version": 2, "prompt_version": "cefr-course-v2", "generation_key": "", "source_manifest": manifest, "courses": [{"title": course["title"], "description": course["description"], "language": "en", "level": "A1", "tags": course["tags"], "units": units}], "quality": {"blocking_errors": [], "warnings": ["LexiLingo-original prose is identified in vocabulary lineage; approved sources supply lexical or pronunciation records only."], "metrics": {"course_count": 1, "unit_count": 3, "lesson_count": 9, "vocabulary_count": 90, "exercise_count": 90}}}
    artifact["generation_key"] = _sha({"builder": "a1-demo-artifact-v1", "blueprint": blueprint, "lexical_record_checksums": sorted(_sha(record) for record in records.values())})
    return artifact

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic offline course-artifact-v2 from the original A1 blueprint and verified lexical records.")
    parser.add_argument("--output", required=True, type=Path, help="Caller-provided JSON output path.")
    parser.add_argument("--lexical-records", type=Path, default=DEFAULT_LEXICAL, help="lexical-records-v1.json (default: beside the blueprint).")
    parser.add_argument("--blueprint", type=Path, default=DEFAULT_BLUEPRINT, help="Approved original curriculum blueprint.")
    args = parser.parse_args(argv)
    try:
        artifact = build(_load(args.blueprint, "blueprint"), _load(args.lexical_records, "lexical input"))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except BuildError as exc:
        print(f"build rejected: {exc}", file=sys.stderr)
        return 2
    print(f"built {args.output} courses=1 units=3 lessons=9 vocabulary=90 exercises=90")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
