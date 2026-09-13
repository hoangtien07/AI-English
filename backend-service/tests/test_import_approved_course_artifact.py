from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "import_approved_course_artifact.py"
spec = importlib.util.spec_from_file_location("import_approved_course_artifact", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
REGISTER = Path(__file__).parents[2] / "docs/demo-data/open-data-source-register-v1.json"


def _inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, dict, dict]:
    root = tmp_path / "repo"; (root / "docs/demo-data").mkdir(parents=True)
    backend = root / "backend-service"; backend.mkdir()
    monkeypatch.setattr(module, "_REPOSITORY_ROOT", root); monkeypatch.setattr(module, "_BACKEND_ROOT", backend)
    register = json.loads(REGISTER.read_text(encoding="utf-8")); register_path = root / "docs/demo-data/open-data-source-register-v1.json"
    register_path.write_text(json.dumps(register), encoding="utf-8"); monkeypatch.setattr(module, "_REGISTER_PATH", register_path)
    fixture = Path(__file__).parents[2] / "contracts/content-agent/fixtures/licensed-etl-artifact-v2.json"
    artifact = json.loads(fixture.read_text(encoding="utf-8")); pin = register["sources"][0]
    manifest = artifact["source_manifest"][0]
    for key in ("source_version", "snapshot_id", "raw_checksum", "license_id", "official_url"):
        manifest[key] = pin[key]
    for course in artifact["courses"]:
        for unit in course["units"]:
            for lesson in unit["lessons"]:
                for vocabulary in lesson["vocabulary"]:
                    vocabulary["raw_checksum"] = pin["raw_checksum"]
    artifact_path = root / "artifact.json"; artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    return artifact_path, register_path, artifact, register


def test_canonical_register_path_schema_and_exact_oewn_cmudict_cefrj_pins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _, _, _, register = _inputs(tmp_path, monkeypatch)
    approved = module._registered_entries(register)
    assert {entry["source_id"] for entry in approved} == {"source-oewn-2025", "source-cmudict", "source-cefr-j"}
    expected = {"source-oewn-2025": ("oewn", "2025"), "source-cmudict": ("cmudict", "74790861f652b15e4ac49015a90074ad62a27690"), "source-cefr-j": ("cefr_j", "d4e45b75b38f27b30dfc5c44d8c571aec7e7092f")}
    assert {(e["source_id"], e["artifact_source_name"], e["source_version"]) for e in approved} == {(sid, name, version) for sid, (name, version) in expected.items()}


def test_default_dry_run_is_zero_write(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    artifact, register, _, _ = _inputs(tmp_path, monkeypatch)
    before = artifact.read_bytes(); assert module.main(["--artifact", str(artifact)]) == 0
    assert artifact.read_bytes() == before and register.exists() and "dry_run=true writes=0" in capsys.readouterr().out


@pytest.mark.parametrize("mutate", [
    lambda r: r.clear(), lambda r: r.update({"sources": []}), lambda r: r["sources"].pop(),
    lambda r: r["sources"][0].update({"raw_checksum": "f" * 64}),
    lambda r: r["sources"][0].update({"license_id": "CC-BY-SA-4.0"}),
    lambda r: r["sources"][3].update({"status": "approved"}),
])
def test_arbitrary_or_tampered_register_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutate) -> None:
    artifact, register_path, _, register = _inputs(tmp_path, monkeypatch); mutate(register); register_path.write_text(json.dumps(register), encoding="utf-8")
    assert module.main(["--artifact", str(artifact)]) == 2


@pytest.mark.parametrize("name", ["alternate.json", "outside.json"])
def test_only_canonical_repository_register_is_used(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str) -> None:
    artifact, register_path, _, register = _inputs(tmp_path, monkeypatch)
    alternate = register_path.parent / name
    alternate.write_text(json.dumps({"sources": []}), encoding="utf-8")
    # The removed override cannot replace the canonical repository register.
    assert module.main(["--artifact", str(artifact)]) == 0
    with pytest.raises(SystemExit):
        module.main(["--artifact", str(artifact), "--source-register", str(alternate)])


def test_artifact_out_of_root_oversized_and_deep_inputs_fail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    artifact, _, _, _ = _inputs(tmp_path, monkeypatch)
    assert module.main(["--artifact", str(tmp_path / "missing.json")]) == 2
    outside = tmp_path / "outside.json"; outside.write_text("{}", encoding="utf-8")
    assert module.main(["--artifact", str(outside)]) == 2
    huge = json.loads(artifact.read_text(encoding="utf-8")); huge["courses"][0]["description"] = "x" * (module._MAX_STRING_BYTES + 1); artifact.write_text(json.dumps(huge), encoding="utf-8")
    assert module.main(["--artifact", str(artifact)]) == 2
    deep: object = "leaf"
    for _ in range(module._MAX_JSON_DEPTH + 2): deep = [deep]
    artifact.write_text(json.dumps({"nested": deep}), encoding="utf-8")
    assert module.main(["--artifact", str(artifact)]) == 2


def test_symlink_artifact_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    artifact, _, _, _ = _inputs(tmp_path, monkeypatch); link = artifact.with_name("link.json")
    try: link.symlink_to(artifact)
    except (OSError, NotImplementedError): pytest.skip("symlinks unavailable in this environment")
    assert module.main(["--artifact", str(link)]) == 2


def test_blocked_evergreen_and_common_voice_are_not_approved() -> None:
    register = json.loads(REGISTER.read_text(encoding="utf-8")); entries = {e["artifact_source_name"]: e for e in register["sources"]}
    assert entries["oer_curriculum"]["status"] == "blocked"; assert entries["oer_curriculum"]["raw_checksum"] is None
    assert "common_voice" not in entries


def test_apply_requires_strict_local_database_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    artifact, _, _, _ = _inputs(tmp_path, monkeypatch)
    assert module.main(["--artifact", str(artifact), "--apply"]) == 2
    monkeypatch.setattr(module, "_require_local_database", lambda: (_ for _ in ()).throw(module.ImportValidationError("strict guard")))
    assert module.main(["--artifact", str(artifact), "--apply", "--local-database"]) == 2


def test_apply_delegates_as_draft_without_duplicate_writes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    artifact, _, payload, _ = _inputs(tmp_path, monkeypatch); calls: list[dict] = []
    monkeypatch.setattr(module, "_require_local_database", lambda: None)
    async def fake_apply(value, pins, *, import_identity=None): calls.append(value); return "job-1", ["course-1"]
    monkeypatch.setattr(module, "_apply", fake_apply)
    assert module.main(["--artifact", str(artifact), "--apply", "--local-database"]) == 0
    assert calls == [payload] and "draft=true" in capsys.readouterr().out


def test_import_identity_64_hex_validation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _, _, artifact, register = _inputs(tmp_path, monkeypatch)
    pins = module._validate_register(artifact, register)

    # Valid generation_key is 64 lowercase hex
    valid_key = "a" * 64
    artifact_copy = dict(artifact, generation_key=valid_key)
    identity = module._import_identity(artifact_copy, pins, new_revision=False)
    assert len(identity) == 64 and module._SHA256_RE.fullmatch(identity)

    # Invalid generation_key variations rejected
    for invalid_key in ["A" * 64, "a" * 63, "a" * 65, "g" * 64, " " * 64, 12345, None, ""]:
        bad_artifact = dict(artifact, generation_key=invalid_key)
        with pytest.raises(module.ImportValidationError, match="artifact generation_key must be normalized 64-hex"):
            module._import_identity(bad_artifact, pins, new_revision=False)

    # Unnormalized or invalid pin raw_checksum rejected
    for invalid_checksum in ["A" * 64, "b" * 63, "g" * 64, None, ""]:
        bad_pins = [dict(pins[0], raw_checksum=invalid_checksum)]
        with pytest.raises(module.ImportValidationError, match="validated source pin is not normalized"):
            module._import_identity(artifact_copy, bad_pins, new_revision=False)

    # Missing required pin field rejected
    for field in ("source_name", "source_version", "snapshot_id", "license_id", "official_url"):
        bad_pins = [dict(pins[0], **{field: None})]
        with pytest.raises(module.ImportValidationError, match="validated source pin is not normalized"):
            module._import_identity(artifact_copy, bad_pins, new_revision=False)


def test_canonical_source_manifest_ordering(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _, _, artifact, register = _inputs(tmp_path, monkeypatch)
    pins = module._validate_register(artifact, register)

    manifest_a = {
        "source_name": "oewn",
        "source_version": "2025",
        "snapshot_id": "snap-1",
        "official_url": "https://example.com/oewn",
        "license_id": "CC-BY-4.0",
        "raw_checksum": "a" * 64,
    }
    manifest_b = {
        "source_name": "cmudict",
        "source_version": "1.0",
        "snapshot_id": "snap-2",
        "official_url": "https://example.com/cmudict",
        "license_id": "BSD-2-Clause",
        "raw_checksum": "b" * 64,
    }

    artifact_1 = dict(artifact, source_manifest=[manifest_a, manifest_b])
    artifact_2 = dict(artifact, source_manifest=[manifest_b, manifest_a])

    # Canonical bytes are invariant to source_manifest order
    assert module._canonical_artifact_bytes(artifact_1) == module._canonical_artifact_bytes(artifact_2)

    # Import identity is invariant to source_manifest order
    id_1 = module._import_identity(artifact_1, pins, new_revision=False)
    id_2 = module._import_identity(artifact_2, pins, new_revision=False)
    assert id_1 == id_2

    # Import identity is invariant to input pins order
    id_pins_1 = module._import_identity(artifact_1, [manifest_a, manifest_b], new_revision=False)
    id_pins_2 = module._import_identity(artifact_1, [manifest_b, manifest_a], new_revision=False)
    assert id_pins_1 == id_pins_2

    # Course content ordering is preserved and affects canonical bytes and identity
    courses_orig = artifact_1["courses"]
    courses_reversed = list(reversed(courses_orig))
    artifact_diff_courses = dict(artifact_1, courses=courses_reversed)
    # If course content or order differs, identity differs
    if courses_orig != courses_reversed:
        assert module._canonical_artifact_bytes(artifact_1) != module._canonical_artifact_bytes(artifact_diff_courses)
        assert module._import_identity(artifact_1, pins, new_revision=False) != module._import_identity(artifact_diff_courses, pins, new_revision=False)

    # Non-list source_manifest raises ImportValidationError
    with pytest.raises(module.ImportValidationError, match="artifact requires a source_manifest"):
        module._canonical_artifact_bytes(dict(artifact, source_manifest=None))


def test_new_revision_generates_deterministic_distinct_identity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    artifact_path, _, artifact, register = _inputs(tmp_path, monkeypatch)
    pins = module._validate_register(artifact, register)

    base_id = module._import_identity(artifact, pins, new_revision=False)
    rev_id = module._import_identity(artifact, pins, new_revision=True)

    assert module._SHA256_RE.fullmatch(base_id)
    assert module._SHA256_RE.fullmatch(rev_id)
    assert base_id != rev_id

    # Deterministic: repeated call produces exact same revision identity
    rev_id_repeat = module._import_identity(artifact, pins, new_revision=True)
    assert rev_id == rev_id_repeat

    # CLI dry run without --new-revision prints base identity
    capsys.readouterr()
    assert module.main(["--artifact", str(artifact_path)]) == 0
    out_base = capsys.readouterr().out
    assert f"import_identity={base_id}" in out_base

    # CLI dry run with --new-revision prints revision identity
    assert module.main(["--artifact", str(artifact_path), "--new-revision"]) == 0
    out_rev = capsys.readouterr().out
    assert f"import_identity={rev_id}" in out_rev


class _FakeTx:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


class _FakeSession:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    def begin(self):
        return _FakeTx()


class _FakeEngine:
    async def dispose(self):
        pass


def test_apply_created_import_validates_before_preview_and_applies_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _, _, artifact, register = _inputs(tmp_path, monkeypatch)
    pins = module._validate_register(artifact, register)

    class FakeJob:
        id = "new-job-uuid-444"
        status = "queued"

    job_instance = FakeJob()

    async def fake_get_or_create(*args, **kwargs):
        return job_instance, True

    transitions: list[tuple[str, int | None]] = []

    async def fake_transition(_db, job, status, *, percent=None, **_kwargs):
        transitions.append((status, percent))
        job.status = status
        return job

    async def fake_set_preview(_db, job, **_kwargs):
        assert job.status == "validating"
        job.status = "preview_ready"
        return job

    class FakeAppliedJob:
        id = "new-job-uuid-444"

    async def fake_apply(_db, job_id):
        assert job_id == "new-job-uuid-444"
        assert job_instance.status == "preview_ready"
        return FakeAppliedJob(), ["course-1"]

    from app.services.content_agent_apply import ContentAgentApplyService
    from app.services.content_agent_jobs import ContentAgentJobService
    import app.core.database as app_db

    monkeypatch.setattr(ContentAgentJobService, "get_or_create_import_job", fake_get_or_create)
    monkeypatch.setattr(ContentAgentJobService, "transition", fake_transition)
    monkeypatch.setattr(ContentAgentJobService, "set_preview", fake_set_preview)
    monkeypatch.setattr(ContentAgentApplyService, "apply", fake_apply)
    monkeypatch.setattr(app_db, "AsyncSessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(app_db, "engine", _FakeEngine())

    import asyncio

    job_id, course_ids, state = asyncio.run(module._apply(artifact, pins))

    assert (job_id, course_ids, state) == ("new-job-uuid-444", ["course-1"], "applied")
    assert transitions == [("validating", 90)]


def test_apply_exact_completed_replay_returns_existing_job_without_apply(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact_path, _, artifact, register = _inputs(tmp_path, monkeypatch)
    pins = module._validate_register(artifact, register)
    monkeypatch.setattr(module, "_require_local_database", lambda: None)

    # Test completed replay with course_ids
    class FakeCompletedJob:
        id = "completed-job-uuid-111"
        status = "completed"
        created_entity_ids = {"course_ids": ["course-101", "course-102"]}

    async def fake_get_or_create(*args, **kwargs):
        return FakeCompletedJob(), False

    from app.services.content_agent_jobs import ContentAgentJobService
    from app.services.content_agent_apply import ContentAgentApplyService
    monkeypatch.setattr(ContentAgentJobService, "get_or_create_import_job", fake_get_or_create)

    apply_called = []
    monkeypatch.setattr(ContentAgentApplyService, "apply", lambda *a, **kw: apply_called.append(True))
    set_preview_called = []
    monkeypatch.setattr(ContentAgentJobService, "set_preview", lambda *a, **kw: set_preview_called.append(True))

    import app.core.database as app_db
    monkeypatch.setattr(app_db, "AsyncSessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(app_db, "engine", _FakeEngine())

    import asyncio
    job_id, course_ids, state = asyncio.run(module._apply(artifact, pins))
    assert job_id == "completed-job-uuid-111"
    assert course_ids == ["course-101", "course-102"]
    assert state == "replayed"
    assert not apply_called, "ContentAgentApplyService.apply must not be called on completed replay"
    assert not set_preview_called, "set_preview must not be called on completed replay"

    # Test fallback to "courses" key
    FakeCompletedJob.created_entity_ids = {"courses": ["course-legacy-99"]}
    job_id_fb, course_ids_fb, state_fb = asyncio.run(module._apply(artifact, pins))
    assert course_ids_fb == ["course-legacy-99"]
    assert state_fb == "replayed"

    # Test CLI output formatting
    async def fake_apply_replay(*a, **kw):
        return "completed-job-uuid-111", ["course-101", "course-102"], "replayed"
    monkeypatch.setattr(module, "_apply", fake_apply_replay)

    capsys.readouterr()
    exit_code = module.main(["--artifact", str(artifact_path), "--apply", "--local-database"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "replayed job_id=completed-job-uuid-111 course_count=2 course_ids=course-101,course-102 draft=true" in out


@pytest.mark.parametrize("active_status", ["queued", "validating", "resolving_sources", "extracting", "preview_ready", "applying"])
def test_apply_active_replay_returns_active_without_apply(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], active_status: str
) -> None:
    artifact_path, _, artifact, register = _inputs(tmp_path, monkeypatch)
    pins = module._validate_register(artifact, register)
    monkeypatch.setattr(module, "_require_local_database", lambda: None)

    class FakeActiveJob:
        id = "active-job-uuid-222"
        status = active_status

    async def fake_get_or_create(*args, **kwargs):
        return FakeActiveJob(), False

    from app.services.content_agent_jobs import ContentAgentJobService
    from app.services.content_agent_apply import ContentAgentApplyService
    monkeypatch.setattr(ContentAgentJobService, "get_or_create_import_job", fake_get_or_create)

    apply_called = []
    monkeypatch.setattr(ContentAgentApplyService, "apply", lambda *a, **kw: apply_called.append(True))
    set_preview_called = []
    monkeypatch.setattr(ContentAgentJobService, "set_preview", lambda *a, **kw: set_preview_called.append(True))

    import app.core.database as app_db
    monkeypatch.setattr(app_db, "AsyncSessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(app_db, "engine", _FakeEngine())

    import asyncio
    job_id, course_ids, state = asyncio.run(module._apply(artifact, pins))
    assert job_id == "active-job-uuid-222"
    assert course_ids == []
    assert state == "active"
    assert not apply_called
    assert not set_preview_called

    # Test CLI output formatting
    async def fake_apply_active(*a, **kw):
        return "active-job-uuid-222", [], "active"
    monkeypatch.setattr(module, "_apply", fake_apply_active)

    capsys.readouterr()
    exit_code = module.main(["--artifact", str(artifact_path), "--apply", "--local-database"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "active job_id=active-job-uuid-222 course_count=0 course_ids= draft=true" in out


@pytest.mark.parametrize("conflict_status", ["failed", "cancelled"])
def test_apply_conflicting_state_rejection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], conflict_status: str
) -> None:
    artifact_path, _, artifact, register = _inputs(tmp_path, monkeypatch)
    pins = module._validate_register(artifact, register)
    monkeypatch.setattr(module, "_require_local_database", lambda: None)

    class FakeConflictingJob:
        id = "conflict-job-uuid-333"
        status = conflict_status

    async def fake_get_or_create(*args, **kwargs):
        return FakeConflictingJob(), False

    from app.services.content_agent_jobs import ContentAgentJobService
    monkeypatch.setattr(ContentAgentJobService, "get_or_create_import_job", fake_get_or_create)

    import app.core.database as app_db
    monkeypatch.setattr(app_db, "AsyncSessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(app_db, "engine", _FakeEngine())

    import asyncio
    with pytest.raises(module.ImportValidationError, match=f"import identity is in conflicting {conflict_status} state"):
        asyncio.run(module._apply(artifact, pins))

    # Test CLI output and return code 2
    async def fake_apply_conflict(*a, **kw):
        raise module.ImportValidationError(f"import identity is in conflicting {conflict_status} state")
    monkeypatch.setattr(module, "_apply", fake_apply_conflict)

    capsys.readouterr()
    exit_code = module.main(["--artifact", str(artifact_path), "--apply", "--local-database"])
    assert exit_code == 2
    err = capsys.readouterr().err
    assert f"import rejected: import identity is in conflicting {conflict_status} state" in err


def test_apply_with_new_revision_passes_distinct_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_path, _, artifact, register = _inputs(tmp_path, monkeypatch)
    pins = module._validate_register(artifact, register)
    monkeypatch.setattr(module, "_require_local_database", lambda: None)

    passed_identities = []
    async def fake_apply(value, p, *, import_identity=None):
        passed_identities.append(import_identity)
        return "job-new-rev", ["c-1"], "applied"
    monkeypatch.setattr(module, "_apply", fake_apply)

    rev_id = module._import_identity(artifact, pins, new_revision=True)
    assert module.main(["--artifact", str(artifact_path), "--apply", "--local-database", "--new-revision"]) == 0
    assert passed_identities == [rev_id]


def _setup_local_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    backend = tmp_path / "backend"
    dev_dir = backend / ".local-dev"
    dev_dir.mkdir(parents=True, exist_ok=True)
    sqlite_file = dev_dir / "lexilingo-importer.sqlite3"
    sqlite_file.touch()
    monkeypatch.setattr(module, "_BACKEND_ROOT", backend)
    from app.core.config import settings

    monkeypatch.setattr(settings, "APP_ENV", "development")
    return sqlite_file


@pytest.mark.parametrize("scheme", ["sqlite+aiosqlite", "sqlite"])
def test_require_local_database_accepts_dedicated_sqlite_urls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scheme: str
) -> None:
    sqlite_file = _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATABASE_URL", f"{scheme}:///{sqlite_file.resolve().as_posix()}")
    module._require_local_database()


def test_require_local_database_rejects_non_development_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sqlite_file = _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{sqlite_file.resolve().as_posix()}")
    with pytest.raises(module.ImportValidationError, match="--apply requires the development application profile"):
        module._require_local_database()


@pytest.mark.parametrize("bad_url", [
    "",
    "/lexilingo_dev",
    "lexilingo-importer.sqlite3",
    "sqlite+aiosqlite:///{path}?cache=shared",
    "sqlite+aiosqlite:///{path}?mode=ro",
    "sqlite+aiosqlite:///{path}#frag",
    "sqlite:///{path}?timeout=10",
    "sqlite:///{path}#target",
])
def test_require_local_database_rejects_uri_query_and_fragment_ambiguity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bad_url: str
) -> None:
    sqlite_file = _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    formatted_url = bad_url.format(path=sqlite_file.resolve().as_posix()) if "{path}" in bad_url else bad_url
    monkeypatch.setattr(settings, "DATABASE_URL", formatted_url)
    with pytest.raises(module.ImportValidationError, match="--apply rejects database URI/query ambiguity"):
        module._require_local_database()


@pytest.mark.parametrize("scheme", ["sqlite+aiosqlite", "sqlite"])
@pytest.mark.parametrize("bad_template", [
    "{scheme}://user:pass@/{path}",
    "{scheme}://user@/{path}",
    "{scheme}://localhost/{path}",
    "{scheme}://remote-server/{path}",
    "{scheme}:////unc-server/share/lexilingo-importer.sqlite3",
    "{scheme}:///{backslash_path}",
])
def test_require_local_database_rejects_netloc_credentials_unc_and_backslash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scheme: str, bad_template: str
) -> None:
    sqlite_file = _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    path_posix = sqlite_file.resolve().as_posix()
    backslash_path = str(sqlite_file.resolve()).replace("/", "\\")
    url = bad_template.format(scheme=scheme, path=path_posix, backslash_path=backslash_path)
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    with pytest.raises(module.ImportValidationError, match="--apply requires the dedicated local SQLite development file"):
        module._require_local_database()


@pytest.mark.parametrize("scheme", ["sqlite+aiosqlite", "sqlite"])
@pytest.mark.parametrize("relative_url", [
    "{scheme}:///relative/path/lexilingo-importer.sqlite3",
    "{scheme}:///./lexilingo-importer.sqlite3",
    "{scheme}:///../lexilingo-importer.sqlite3",
    "{scheme}:///lexilingo-importer.sqlite3",
])
def test_require_local_database_rejects_relative_sqlite_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scheme: str, relative_url: str
) -> None:
    _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    url = relative_url.format(scheme=scheme)
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    with pytest.raises(module.ImportValidationError, match="--apply requires the dedicated local SQLite development file"):
        module._require_local_database()


@pytest.mark.parametrize("scheme", ["sqlite+aiosqlite", "sqlite"])
def test_require_local_database_rejects_wrong_or_missing_sqlite_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scheme: str
) -> None:
    sqlite_file = _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    # Wrong file in same directory
    other_file = sqlite_file.parent / "other.sqlite3"
    other_file.touch()
    monkeypatch.setattr(settings, "DATABASE_URL", f"{scheme}:///{other_file.resolve().as_posix()}")
    with pytest.raises(module.ImportValidationError, match="--apply requires the dedicated non-symlink local SQLite development file"):
        module._require_local_database()

    # Missing file (expected file deleted)
    sqlite_file.unlink()
    monkeypatch.setattr(settings, "DATABASE_URL", f"{scheme}:///{sqlite_file.resolve().as_posix()}")
    with pytest.raises(module.ImportValidationError, match="--apply requires the dedicated non-symlink local SQLite development file"):
        module._require_local_database()


@pytest.mark.parametrize("scheme", ["sqlite+aiosqlite", "sqlite"])
def test_require_local_database_rejects_symlink_sqlite_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scheme: str
) -> None:
    sqlite_file = _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    symlink_file = sqlite_file.parent / "symlink-importer.sqlite3"
    try:
        symlink_file.symlink_to(sqlite_file)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable in this environment")

    # Symlink pointing to the real file
    monkeypatch.setattr(settings, "DATABASE_URL", f"{scheme}:///{symlink_file.as_posix()}")
    with pytest.raises(module.ImportValidationError, match="--apply requires the dedicated non-symlink local SQLite development file"):
        module._require_local_database()

    # Expected file itself replaced with a symlink pointing to another file
    actual_file = tmp_path / "actual.sqlite3"
    actual_file.touch()
    sqlite_file.unlink()
    try:
        sqlite_file.symlink_to(actual_file)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable in this environment")

    monkeypatch.setattr(settings, "DATABASE_URL", f"{scheme}:///{sqlite_file.as_posix()}")
    with pytest.raises(module.ImportValidationError, match="--apply requires the dedicated non-symlink local SQLite development file"):
        module._require_local_database()


@pytest.mark.parametrize("invalid_pg_url", [
    "mysql://lexilingo_dev@localhost:5432/lexilingo_dev",
    "postgresql+asyncpg://lexilingo_dev@remote.internal:5432/lexilingo_dev",
    "postgresql+asyncpg://lexilingo_dev@192.168.1.1:5432/lexilingo_dev",
    "postgresql+asyncpg://lexilingo_dev@localhost:5433/lexilingo_dev",
    "postgresql+asyncpg://other_user@localhost:5432/lexilingo_dev",
    "postgresql+asyncpg://lexilingo_dev@localhost:5432/other_db",
    "postgresql+asyncpg://lexilingo_dev@localhost:5432/",
    "postgresql+asyncpg://lexilingo_dev@localhost/",
])
def test_require_local_database_rejects_invalid_postgresql_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, invalid_pg_url: str
) -> None:
    _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATABASE_URL", invalid_pg_url)
    with pytest.raises(module.ImportValidationError, match="--apply requires strict loopback lexilingo_dev PostgreSQL identity"):
        module._require_local_database()


@pytest.mark.parametrize("valid_pg_url", [
    "postgresql+asyncpg://lexilingo_dev@localhost/lexilingo_dev",
    "postgresql+asyncpg://lexilingo_dev@localhost:5432/lexilingo_dev",
    "postgresql://lexilingo_dev@127.0.0.1:5432/lexilingo_dev",
    "postgres://lexilingo_dev@localhost:5432/lexilingo_dev",
    "postgresql+asyncpg://lexilingo_dev@[::1]:5432/lexilingo_dev",
])
def test_require_local_database_accepts_valid_loopback_postgresql(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, valid_pg_url: str
) -> None:
    _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATABASE_URL", valid_pg_url)
    module._require_local_database()


def test_require_compose_local_database_accepts_exact_compose_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql+asyncpg://lexilingo:test-password@postgres:5432/lexilingo")
    module._require_compose_local_database()


@pytest.mark.parametrize("invalid_pg_url", [
    "postgres://lexilingo@postgres:5432/lexilingo",
    "postgresql://lexilingo@postgres:5432/lexilingo",
    "postgresql+asyncpg://lexilingo@localhost:5432/lexilingo",
    "postgresql+asyncpg://lexilingo@postgres:5433/lexilingo",
    "postgresql+asyncpg://lexilingo@postgres/lexilingo",
    "postgresql+asyncpg://other_user@postgres:5432/lexilingo",
    "postgresql+asyncpg://lexilingo@postgres:5432/lexilingo",
    "postgresql+asyncpg://lexilingo:@postgres:5432/lexilingo",
    "postgresql+asyncpg://lexilingo@postgres:5432/other_db",
    "postgresql+asyncpg://lexilingo@postgres:5432/",
    "postgresql+asyncpg://lexilingo@postgres:5432/lexilingo?ssl=false",
    "postgresql+asyncpg://lexilingo@postgres:5432/lexilingo#fragment",
])
def test_require_compose_local_database_rejects_any_identity_deviation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, invalid_pg_url: str
) -> None:
    _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATABASE_URL", invalid_pg_url)
    with pytest.raises(module.ImportValidationError):
        module._require_compose_local_database()


def test_require_compose_local_database_rejects_non_development_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _setup_local_sqlite(tmp_path, monkeypatch)
    from app.core.config import settings

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql+asyncpg://lexilingo:test-password@postgres:5432/lexilingo")
    with pytest.raises(module.ImportValidationError, match="--compose-local requires the development application profile"):
        module._require_compose_local_database()


def test_apply_compose_local_uses_compose_guard_and_invokes_apply(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact, _, payload, _ = _inputs(tmp_path, monkeypatch)
    guards: list[str] = []
    calls: list[dict] = []

    monkeypatch.setattr(module, "_require_local_database", lambda: guards.append("local"))
    monkeypatch.setattr(module, "_require_compose_local_database", lambda: guards.append("compose"))

    async def fake_apply(value, pins, *, import_identity=None):
        calls.append(value)
        return "job-1", ["course-1"], "applied"

    monkeypatch.setattr(module, "_apply", fake_apply)
    assert module.main(["--artifact", str(artifact), "--apply", "--compose-local"]) == 0
    assert guards == ["compose"]
    assert calls == [payload]


def test_apply_rejects_combined_database_target_acknowledgements(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact, _, _, _ = _inputs(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "_require_local_database", lambda: pytest.fail("local guard must not run"))
    monkeypatch.setattr(module, "_require_compose_local_database", lambda: pytest.fail("compose guard must not run"))

    with pytest.raises(SystemExit) as exc_info:
        module.main([
            "--artifact", str(artifact), "--apply", "--local-database", "--compose-local"
        ])
    assert exc_info.value.code == 2


@pytest.mark.parametrize("scheme", ["sqlite+aiosqlite", "sqlite"])
def test_apply_cli_with_dedicated_sqlite_urls_invokes_apply(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scheme: str
) -> None:
    artifact, _, payload, _ = _inputs(tmp_path, monkeypatch)
    from app.core.config import settings

    sqlite_dir = module._BACKEND_ROOT / ".local-dev"
    sqlite_dir.mkdir(parents=True, exist_ok=True)
    sqlite_file = sqlite_dir / "lexilingo-importer.sqlite3"
    sqlite_file.touch()

    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DATABASE_URL", f"{scheme}:///{sqlite_file.resolve().as_posix()}")

    calls: list[dict] = []
    async def fake_apply(value, pins, *, import_identity=None):
        calls.append(value)
        return "job-1", ["course-1"], "applied"

    monkeypatch.setattr(module, "_apply", fake_apply)
    assert module.main(["--artifact", str(artifact), "--apply", "--local-database"]) == 0
    assert calls == [payload]
