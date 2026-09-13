import json
from pathlib import Path
from typing import get_args

import jsonschema
import pytest
from pydantic import ValidationError

from app.schemas.content_agent import (
    ArtifactSourceManifest,
    ArtifactSourceName,
    CEFRLevel,
    ContentAgentArtifact,
    NormalizedVocabularyRecord,
    PartOfSpeech,
    SourceSnapshotDescriptor,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = REPO_ROOT / "contracts" / "content-agent"


def _contract(filename: str) -> dict:
    return json.loads((CONTRACT_ROOT / filename).read_text(encoding="utf-8"))


def _valid_manifest_payload(source_name: str) -> dict:
    return {
        "snapshot_id": f"{source_name}:2025:" + ("a" * 64),
        "source_name": source_name,
        "source_version": "2025",
        "official_url": "https://example.com/source",
        "license_id": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution_text": "Attribution notice",
        "retrieved_at": "2026-06-15T00:00:00Z",
        "raw_checksum": "a" * 64,
        "normalized_sha256": "b" * 64,
        "normalized_bytes": 1024,
        "record_checksum_root": "c" * 64,
        "adapter_version": 1,
        "record_count": 10,
    }


def _valid_descriptor_payload(source_name: str) -> dict:
    payload = _valid_manifest_payload(source_name)
    payload["source_id"] = f"{source_name}-id"
    payload["enabled"] = True
    return payload


def test_shared_source_contract_matches_backend_enums_and_strictness():
    contract = _contract("source-record-v2.schema.json")

    assert set(contract["$defs"]["cefrLevel"]["enum"]) == set(get_args(CEFRLevel))
    assert set(contract["$defs"]["partOfSpeech"]["enum"]) == set(
        get_args(PartOfSpeech)
    )
    assert contract["additionalProperties"] is False
    assert contract["properties"]["topic_ids"]["uniqueItems"] is True
    assert {
        "schema_version",
        "record_id",
        "source_name",
        "source_version",
        "source_record_id",
        "source_url",
        "license_id",
        "license_url",
        "attribution_text",
        "content_usage",
        "language",
        "retrieved_at",
        "raw_checksum",
        "record_checksum",
        "lineage",
    }.issubset(contract["required"])
    assert NormalizedVocabularyRecord.model_config["extra"] == "forbid"


def test_shared_contracts_source_name_enum_matches_backend():
    course_contract = _contract("course-artifact-v2.schema.json")
    source_contract = _contract("source-record-v2.schema.json")

    course_sources = set(
        course_contract["$defs"]["sourceManifest"]["properties"]["source_name"]["enum"]
    )
    record_sources = set(source_contract["properties"]["source_name"]["enum"])
    backend_sources = set(get_args(ArtifactSourceName))

    assert course_sources == record_sources
    assert backend_sources == course_sources
    assert "oer_curriculum" in backend_sources


def test_backend_manifest_and_descriptor_accept_every_contract_source_name():
    contract = _contract("course-artifact-v2.schema.json")
    enum_sources = contract["$defs"]["sourceManifest"]["properties"]["source_name"]["enum"]

    for source in enum_sources:
        manifest = ArtifactSourceManifest.model_validate(_valid_manifest_payload(source))
        assert manifest.source_name == source

        descriptor = SourceSnapshotDescriptor.model_validate(_valid_descriptor_payload(source))
        assert descriptor.source_name == source


@pytest.mark.parametrize("invalid_source", ["unknown", "scraped", "wikipedia", "INVALID"])
def test_backend_manifest_and_descriptor_reject_unknown_source_name(invalid_source):
    with pytest.raises(ValidationError):
        ArtifactSourceManifest.model_validate(_valid_manifest_payload(invalid_source))

    with pytest.raises(ValidationError):
        SourceSnapshotDescriptor.model_validate(_valid_descriptor_payload(invalid_source))


def test_source_record_contract_rejects_duplicate_topic_ids():
    contract = _contract("source-record-v2.schema.json")
    record = {
        "schema_version": 2,
        "record_id": "test:1",
        "source_name": "oewn",
        "source_version": "2025",
        "source_record_id": "rec-1",
        "source_url": "https://en-word.net/lemma/test",
        "license_id": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution_text": "Test Attribution",
        "content_usage": "lexical",
        "language": "en",
        "definition": "A test definition.",
        "retrieved_at": "2026-06-15T00:00:00Z",
        "raw_checksum": "a" * 64,
        "record_checksum": "b" * 64,
        "lineage": {
            "adapter": "oewn",
            "adapter_version": 1,
            "raw_path": "test.xml",
            "source_location": "rec-1",
        },
        "topic_ids": ["topic1", "topic2", "topic1"],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=record, schema=contract)

    record["topic_ids"] = ["topic1", "topic2"]
    jsonschema.validate(instance=record, schema=contract)


def test_shared_course_artifact_contract_matches_backend_version():
    contract = _contract("course-artifact-v2.schema.json")

    assert contract["properties"]["schema_version"]["const"] == 2
    assert contract["properties"]["prompt_version"]["const"] == "cefr-course-v2"
    assert ContentAgentArtifact.model_fields["schema_version"].default == 2
    assert (
        ContentAgentArtifact.model_fields["prompt_version"].default
        == "cefr-course-v2"
    )
    assert ContentAgentArtifact.model_config["extra"] == "forbid"
    manifest = contract["properties"]["source_manifest"]
    assert manifest["minItems"] == 1
    assert manifest["items"]["$ref"] == "#/$defs/sourceManifest"
    assert contract["$defs"]["sourceManifest"]["additionalProperties"] is False
    assert {
        "raw_checksum",
        "normalized_sha256",
        "normalized_bytes",
        "record_checksum_root",
    }.issubset(contract["$defs"]["sourceManifest"]["required"])


def test_shared_exercise_mapping_contains_every_supported_base_type():
    exercise_contract = _contract("exercise-types-v1.json")
    artifact_contract = _contract("course-artifact-v2.schema.json")

    assert set(exercise_contract["base_types"]) == set(
        artifact_contract["$defs"]["exercise"]["properties"]["type"]["enum"]
    )


def test_backend_ui_type_mapping_matches_the_contract():
    """The mapping is duplicated in app/models/course.py because the contract
    file is not shipped in the backend image."""
    from app.models.course import UI_TYPE_TO_BASE_TYPE

    contract = _contract("exercise-types-v1.json")

    assert UI_TYPE_TO_BASE_TYPE == contract["ui_type_to_type"]
    assert set(UI_TYPE_TO_BASE_TYPE.values()) <= set(contract["base_types"])
