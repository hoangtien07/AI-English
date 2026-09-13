from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from api.services.content_etl.adapters.oer_curriculum import LICENSE_ID, LICENSE_URL, MAX_RECORDS, MAX_SCOPE_ITEMS, MAX_SNAPSHOT_BYTES, MAX_TEXT_LENGTH, OERCurriculumAdapter, _sha256
from api.services.content_etl.contracts import AllowedLicenseId, SourceName
from api.services.content_etl.downloader import DownloadSecurityError, SecureDownloader
from api.services.content_etl.storage import SnapshotStorage

EVERGREEN = "https://human.libretexts.org/Courses/Evergreen_Valley_College/Listening_and_Speaking_for_Beginning_English_Language_Learners"


def _json_snapshot(tmp_path: Path, **changes: object) -> Path:
    payload: dict[str, object] = {"schema_version": 1, "source": {"source_version": "2026.1", "source_url": EVERGREEN, "license_id": LICENSE_ID, "license_url": LICENSE_URL, "attribution_text": "Synthetic offline curriculum outline"}, "curriculum": {"title": "Everyday topics", "outcome": "Describe daily routines", "units": [{"title": "Introductions", "lessons": [{"title": "Names", "topic": "greetings"}]}]}}
    payload.update(changes)
    without = json.loads(json.dumps(payload))
    without["source"].pop("raw_checksum", None)
    payload["source"]["raw_checksum"] = _sha256(json.dumps(without, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    path = tmp_path / "outline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_json_outline_is_deterministic_and_metadata_only(tmp_path: Path) -> None:
    first = OERCurriculumAdapter().parse(_json_snapshot(tmp_path))
    second = OERCurriculumAdapter().parse(_json_snapshot(tmp_path))
    assert first == second
    assert {item["metadata"]["record_type"] for item in first} == {"course", "unit", "lesson"}
    assert all(item["source_url"] == EVERGREEN and item["content_usage"] == "topic" for item in first)
    assert all("exercises" not in item and "prose" not in item for item in first)


def test_oer_policy_is_exact_and_arbitrary_provenance_is_rejected(tmp_path: Path) -> None:
    assert SourceName.OER_CURRICULUM.value == "oer_curriculum"
    assert AllowedLicenseId.CC_BY_4_0.value == LICENSE_ID
    from api.services.content_etl.contracts import _SOURCE_ALLOWED_LICENSES
    assert _SOURCE_ALLOWED_LICENSES["oer_curriculum"] == frozenset({LICENSE_ID})
    for url in ["https://example.test/oer/curriculum", EVERGREEN + "?download=1", EVERGREEN + "/other"]:
        path = _json_snapshot(tmp_path)
        payload = json.loads(path.read_text(encoding="utf-8")); payload["source"]["source_url"] = url
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError):
            OERCurriculumAdapter().parse(path)


def test_html_checksum_failure_regression_is_fixed_and_body_media_is_ignored(tmp_path: Path) -> None:
    body = f'''<html><head><meta name="oer:source-version" content="2026.1"><meta name="oer:source-url" content="{EVERGREEN}"><meta name="oer:license-id" content="CC-BY-4.0"><meta name="oer:license-url" content="{LICENSE_URL}"><meta name="oer:attribution-text" content="Synthetic offline curriculum outline"></head><body><h1>Everyday topics</h1><script>alert('bad')</script><p>Copied prose must not enter records.</p><img src="data:image/png;base64,AA=="></img><h2>Introductions</h2><iframe src="https://example.test/media"></iframe><h3 data-oer-topic="greetings">Names</h3><video>media</video></body></html>'''.encode()
    digest = hashlib.sha256(body).hexdigest(); raw = body.replace(b"</head>", f'<meta name="oer:raw-checksum" content="{digest}"></head>'.encode())
    path = tmp_path / "outline.html"; path.write_bytes(raw)
    records = OERCurriculumAdapter().parse(path)
    assert [record["metadata"]["title"] for record in records] == ["Everyday topics", "Introductions", "Names"]
    serialized = json.dumps(records)
    assert "Copied prose" not in serialized and "alert" not in serialized and "media" not in serialized


@pytest.mark.parametrize("field,value", [("license_id", "CC-BY-SA-4.0"), ("license_url", "https://example.test/license"), ("source_version", "")])
def test_provenance_policy_rejects_wrong_metadata(tmp_path: Path, field: str, value: str) -> None:
    path = _json_snapshot(tmp_path); payload = json.loads(path.read_text(encoding="utf-8")); payload["source"][field] = value
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError): OERCurriculumAdapter().parse(path)


def test_oer_checksum_markup_and_text_scope_bounds_are_deterministic(tmp_path: Path) -> None:
    path = _json_snapshot(tmp_path); payload = json.loads(path.read_text(encoding="utf-8")); payload["source"]["raw_checksum"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="raw_checksum"): OERCurriculumAdapter().parse(path)
    for field, value in [("title", "x" * (MAX_TEXT_LENGTH + 1)), ("topic", ["x"] * (MAX_SCOPE_ITEMS + 1))]:
        curriculum = {"title": "Everyday topics", "units": [{"title": "Unit", "lessons": [{"title": "Lesson"}]}]}; curriculum[field] = value
        with pytest.raises(ValueError, match="maximum"): OERCurriculumAdapter().parse(_json_snapshot(tmp_path, curriculum=curriculum))
    many = [{"title": f"u{i}", "lessons": [{"title": "l"}]} for i in range(MAX_RECORDS // 2 + 2)]
    with pytest.raises(ValueError, match="maximum record count"): OERCurriculumAdapter().parse(_json_snapshot(tmp_path, curriculum={"title": "Course", "units": many}))


@pytest.mark.asyncio
async def test_generic_downloader_rejects_oer_before_http(tmp_path: Path) -> None:
    called = False
    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called; called = True; return httpx.Response(200, content=b"unexpected")
    downloader = SecureDownloader(storage=SnapshotStorage(tmp_path / "snapshots"), timeout_seconds=2, max_download_bytes=1024, user_agent="tests", transport=httpx.MockTransport(handler))
    with pytest.raises(DownloadSecurityError, match="offline-only"):
        await downloader.download(source_name=SourceName.OER_CURRICULUM, version="2026.1", url=EVERGREEN)
    assert called is False


def test_snapshot_size_limit_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "huge.json"; path.write_bytes(b"x" * (MAX_SNAPSHOT_BYTES + 1))
    with pytest.raises(ValueError, match="maximum size"): OERCurriculumAdapter().parse(path)
