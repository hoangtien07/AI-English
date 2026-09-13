"""Fail-closed offline importer for repository-approved course artifacts."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPOSITORY_ROOT = _BACKEND_ROOT.parent
_REGISTER_PATH = _REPOSITORY_ROOT / "docs" / "demo-data" / "open-data-source-register-v1.json"
_MAX_ARTIFACT_BYTES, _MAX_REGISTER_BYTES = 2 * 1024 * 1024, 128 * 1024
_MAX_JSON_DEPTH, _MAX_JSON_NODES, _MAX_LIST_ITEMS = 32, 50_000, 10_000
_MAX_OBJECT_KEYS, _MAX_STRING_BYTES = 128, 32 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_SOURCE_IDS = frozenset({"source-oewn-2025", "source-cmudict", "source-cefr-j", "source-evc-beginning-ell"})
_APPROVED_SOURCE_IDS = frozenset({"source-oewn-2025", "source-cmudict", "source-cefr-j"})
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class ImportValidationError(ValueError):
    """A fail-closed local input, trust, or database-boundary error."""


def _under_root(path: Path, root: Path, label: str) -> Path:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ImportValidationError(f"{label} must be inside the repository staging root") from exc
    return path


def _no_symlink_components(path: Path, label: str) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                raise ImportValidationError(f"{label} must not traverse a symlink")
        except OSError as exc:
            raise ImportValidationError(f"{label} local file does not exist") from exc


def _local_json_path(raw_path: str, label: str, *, root: Path) -> Path:
    is_windows_drive = isinstance(raw_path, str) and re.match(r"^[A-Za-z]:[\\/]", raw_path)
    if not isinstance(raw_path, str) or (not is_windows_drive and re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw_path)) or raw_path.startswith(("\\\\", "//")):
        raise ImportValidationError(f"{label} must be a local JSON file path")
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    _no_symlink_components(candidate, label)
    try:
        path = candidate.resolve(strict=True)
    except OSError as exc:
        raise ImportValidationError(f"{label} local file does not exist") from exc
    _under_root(path, root, label)
    if path.suffix.lower() != ".json" or not path.is_file():
        raise ImportValidationError(f"{label} must name a regular .json file")
    return path


def _bounded_json(value: Any, label: str, depth: int = 0, counter: list[int] | None = None) -> None:
    if depth > _MAX_JSON_DEPTH:
        raise ImportValidationError(f"{label} exceeds maximum JSON nesting")
    counter = counter if counter is not None else [0]
    counter[0] += 1
    if counter[0] > _MAX_JSON_NODES:
        raise ImportValidationError(f"{label} exceeds maximum JSON structural count")
    if isinstance(value, str):
        if len(value.encode("utf-8")) > _MAX_STRING_BYTES:
            raise ImportValidationError(f"{label} contains an oversized JSON string")
    elif isinstance(value, list):
        if len(value) > _MAX_LIST_ITEMS:
            raise ImportValidationError(f"{label} contains an oversized JSON array")
        for item in value:
            _bounded_json(item, label, depth + 1, counter)
    elif isinstance(value, dict):
        if len(value) > _MAX_OBJECT_KEYS:
            raise ImportValidationError(f"{label} contains an oversized JSON object")
        for key, item in value.items():
            _bounded_json(key, label, depth + 1, counter)
            _bounded_json(item, label, depth + 1, counter)


def _read_json_bytes(path: Path, label: str, max_bytes: int) -> tuple[dict[str, Any], bytes]:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb", closefd=True) as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
                raise ImportValidationError(f"{label} exceeds its bounded local-input limit")
            data = source.read(max_bytes + 1)
            after = os.fstat(source.fileno())
    except ImportValidationError:
        raise
    except OSError as exc:
        raise ImportValidationError(f"{label} is not a safe readable regular file") from exc
    if len(data) > max_bytes or before.st_ino != after.st_ino or before.st_size != after.st_size:
        raise ImportValidationError(f"{label} changed while being read or exceeds its input limit")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImportValidationError(f"{label} is not readable JSON") from exc
    if not isinstance(payload, dict):
        raise ImportValidationError(f"{label} root must be a JSON object")
    _bounded_json(payload, label)
    return payload, data


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ImportValidationError(f"{label} does not match the authoritative register schema")


def _registered_entries(register: dict[str, Any]) -> list[dict[str, Any]]:
    _keys(register, {"schema", "schema_version", "title", "sources"}, "source register")
    if register.get("schema") != "lexilingo.open-data-source-register" or register.get("schema_version") != 2:
        raise ImportValidationError("source register schema/version is not supported")
    sources = register.get("sources")
    if not isinstance(sources, list) or len(sources) != len(_ALLOWED_SOURCE_IDS):
        raise ImportValidationError("source register must contain exactly the approved source set")
    fields = {"source_id", "artifact_source_name", "display_name", "status", "blocked_reason", "source_version", "snapshot_id", "raw_checksum", "license_id", "official_url", "allowed_usage"}
    seen, approved = set(), []
    for entry in sources:
        if not isinstance(entry, dict):
            raise ImportValidationError("source register entries must be objects")
        _keys(entry, fields, "source register entry")
        source_id, status = _text(entry.get("source_id")), entry.get("status")
        if source_id not in _ALLOWED_SOURCE_IDS or source_id in seen or status not in {"approved", "blocked"}:
            raise ImportValidationError("source register has an unknown, duplicate, or invalid-status source")
        seen.add(source_id)
        required = ("artifact_source_name", "display_name", "source_version", "snapshot_id", "license_id", "official_url")
        usages, checksum = entry.get("allowed_usage"), entry.get("raw_checksum")
        if any(_text(entry.get(key)) is None for key in required) or not isinstance(usages, list) or not usages or not all(_text(value) for value in usages):
            raise ImportValidationError("source register entry has invalid required fields")
        if status == "approved":
            if source_id not in _APPROVED_SOURCE_IDS or entry.get("blocked_reason") is not None or not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise ImportValidationError("approved register entry is invalid")
            approved.append({**entry, "allowed_usage": frozenset(usages)})
        elif source_id != "source-evc-beginning-ell" or not _text(entry.get("blocked_reason")) or checksum is not None:
            raise ImportValidationError("blocked register entry is invalid")
    if seen != _ALLOWED_SOURCE_IDS or {entry["source_id"] for entry in approved} != _APPROVED_SOURCE_IDS:
        raise ImportValidationError("source register exact allowlist is incomplete")
    return approved


def _source_usages(artifact: dict[str, Any], source_name: str) -> set[str]:
    usages: set[str] = set()
    for course in artifact.get("courses") or []:
        for unit in course.get("units") or []:
            for lesson in unit.get("lessons") or []:
                for vocabulary in lesson.get("vocabulary") or []:
                    if isinstance(vocabulary, dict) and vocabulary.get("source_name") == source_name:
                        usage = _text(vocabulary.get("content_usage"))
                        if usage is None:
                            raise ImportValidationError("imported vocabulary is missing content_usage")
                        usages.add(usage)
    return usages


def _validate_register(artifact: dict[str, Any], register: dict[str, Any]) -> list[dict[str, Any]]:
    approved, manifests, pins, seen = _registered_entries(register), artifact.get("source_manifest"), [], set()
    if not isinstance(manifests, list) or not manifests:
        raise ImportValidationError("artifact requires a non-empty source_manifest")
    for manifest in manifests:
        if not isinstance(manifest, dict):
            raise ImportValidationError("artifact source_manifest entries must be objects")
        source_name = _text(manifest.get("source_name"))
        if source_name is None or source_name in seen:
            raise ImportValidationError("artifact source_manifest has a missing or duplicate source")
        seen.add(source_name)
        matches = [entry for entry in approved if entry["artifact_source_name"] == source_name and all(entry[key] == manifest.get(key) for key in ("source_version", "snapshot_id", "raw_checksum", "license_id", "official_url"))]
        if not matches:
            raise ImportValidationError("artifact manifest has no exact approved source pin")
        usages = _source_usages(artifact, source_name)
        if not usages or not usages.issubset(matches[0]["allowed_usage"]):
            raise ImportValidationError("artifact usage is not approved by the source register")
        pins.append(manifest)
    return pins


def _validate_artifact(artifact: dict[str, Any], pins: list[dict[str, Any]]) -> dict[str, int]:
    from pydantic import ValidationError
    from app.schemas.content_agent import ContentAgentArtifact
    from app.services.content_agent_validation import validate_artifact
    try:
        ContentAgentArtifact.model_validate(artifact)
    except ValidationError as exc:
        raise ImportValidationError("artifact does not satisfy course-artifact-v2") from exc
    report = validate_artifact(artifact, pinned_snapshots=pins)
    if report.is_blocking:
        raise ImportValidationError("artifact validation failed: " + ",".join(sorted({issue.code for issue in report.blocking_errors})))
    return {name: int(value) for name, value in report.metrics.items() if isinstance(value, int)}


def _canonical_json_bytes(value: Any) -> bytes:
    """The stable byte representation used by import identity, not file formatting."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _canonical_artifact_bytes(artifact: dict[str, Any]) -> bytes:
    """Canonicalize the unordered manifest without changing ordered course content."""
    manifest = artifact.get("source_manifest")
    if not isinstance(manifest, list):
        raise ImportValidationError("artifact requires a source_manifest")
    canonical = dict(artifact)
    canonical["source_manifest"] = sorted(
        manifest,
        key=lambda entry: (
            str(entry.get("source_name", "")) if isinstance(entry, dict) else "",
            str(entry.get("snapshot_id", "")) if isinstance(entry, dict) else "",
        ),
    )
    return _canonical_json_bytes(canonical)


def _import_identity(
    artifact: dict[str, Any], pins: list[dict[str, Any]], *, new_revision: bool
) -> str:
    generation_key = artifact.get("generation_key")
    if not isinstance(generation_key, str) or _SHA256_RE.fullmatch(generation_key) is None:
        raise ImportValidationError("artifact generation_key must be normalized 64-hex")
    canonical_pins: list[dict[str, str]] = []
    for pin in pins:
        normalized = {
            field: _text(pin.get(field))
            for field in (
                "source_name", "source_version", "snapshot_id", "raw_checksum",
                "license_id", "official_url",
            )
        }
        if any(value is None for value in normalized.values()) or _SHA256_RE.fullmatch(normalized["raw_checksum"] or "") is None:
            raise ImportValidationError("validated source pin is not normalized")
        canonical_pins.append(normalized)  # type: ignore[arg-type]
    canonical_pins.sort(key=lambda pin: (pin["source_name"], pin["snapshot_id"]))
    digest = hashlib.sha256()
    # Length-delimited fields prevent ambiguous concatenation and keep this
    # independent of normal content-agent request hashes.
    for part in (
        b"lexilingo-approved-import-v1",
        _canonical_artifact_bytes(artifact),
        _canonical_json_bytes(canonical_pins),
        generation_key.encode("ascii"),
    ):
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    identity = digest.hexdigest()
    if new_revision:
        identity = hashlib.sha256(
            b"lexilingo-approved-import-revision-v1\0" + identity.encode("ascii")
        ).hexdigest()
    return identity


def _require_local_database() -> None:
    from app.core.config import settings
    if not settings.is_development:
        raise ImportValidationError("--apply requires the development application profile")
    raw_url, parsed = settings.DATABASE_URL, urlsplit(settings.DATABASE_URL)
    if not parsed.scheme or parsed.query or parsed.fragment:
        raise ImportValidationError("--apply rejects database URI/query ambiguity")
    if parsed.scheme in {"sqlite", "sqlite+aiosqlite"}:
        # Keep the URL form unambiguous: SQLite is a local file only, and the
        # async driver is required by the application's AsyncEngine.
        if (
            parsed.netloc
            or parsed.username
            or parsed.password
            or not raw_url.startswith(f"{parsed.scheme}:///")
        ):
            raise ImportValidationError("--apply requires the dedicated local SQLite development file")
        expected = (_BACKEND_ROOT / ".local-dev" / "lexilingo-importer.sqlite3").resolve(strict=False)
        decoded_path = unquote(parsed.path)
        # urlsplit represents a Windows drive path as /C:/...; remove only
        # that URL-introduced slash. Reject relative, UNC, and backslash forms.
        if re.match(r"^/[A-Za-z]:/", decoded_path):
            decoded_path = decoded_path[1:]
        if "\\" in decoded_path:
            raise ImportValidationError("--apply requires the dedicated local SQLite development file")
        if decoded_path.startswith("//"):
            expected_root = expected.as_posix().lstrip("/").split("/", 1)[0]
            candidate_root = decoded_path.lstrip("/").split("/", 1)[0]
            if candidate_root != expected_root:
                raise ImportValidationError("--apply requires the dedicated local SQLite development file")
            decoded_path = "/" + decoded_path.lstrip("/")
        is_windows_absolute = re.match(r"^[A-Za-z]:/", decoded_path) is not None
        is_posix_absolute = decoded_path.startswith("/")
        if not decoded_path or not (is_windows_absolute or is_posix_absolute):
            raise ImportValidationError("--apply requires the dedicated local SQLite development file")
        candidate = Path(decoded_path)
        try:
            db_path = candidate.resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            raise ImportValidationError("--apply requires the dedicated local SQLite development file") from None
        if db_path.parent != expected.parent:
            raise ImportValidationError("--apply requires the dedicated local SQLite development file")
        if db_path != expected or candidate.is_symlink() or not candidate.is_file():
            raise ImportValidationError("--apply requires the dedicated non-symlink local SQLite development file")
        return
    if (
        parsed.scheme not in {"postgres", "postgresql", "postgresql+asyncpg"}
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.port not in {None, 5432}
        or parsed.username != "lexilingo_dev"
        or parsed.password is not None
        or parsed.path != "/lexilingo_dev"
    ):
        raise ImportValidationError("--apply requires strict loopback lexilingo_dev PostgreSQL identity")


def _require_compose_local_database() -> None:
    """Permit an explicit import only into the local Compose development DB.

    This is deliberately narrower than the loopback development target: it is
    for the backend container's internal PostgreSQL address only, never for a
    host, remote network, alternate database, or URI ambiguity.  Compose
    supplies its database password at runtime, so the password is required but
    deliberately never inspected or logged.
    """
    from app.core.config import settings

    if not settings.is_development:
        raise ImportValidationError(
            "--compose-local requires the development application profile"
        )
    parsed = urlsplit(settings.DATABASE_URL)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ImportValidationError(
            "--compose-local requires strict Compose PostgreSQL identity"
        ) from exc
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname != "postgres"
        or port != 5432
        or parsed.username != "lexilingo"
        or not parsed.password
        or parsed.path != "/lexilingo"
        or parsed.query
        or parsed.fragment
    ):
        raise ImportValidationError(
            "--compose-local requires strict Compose PostgreSQL identity"
        )


async def _apply(
    artifact: dict[str, Any], pins: list[dict[str, Any]], *, import_identity: str | None = None
) -> tuple[str, list[str], str]:
    from app.core.database import AsyncSessionLocal, engine
    from app.schemas.content_agent import ContentAgentJobCreate
    from app.services.content_agent_apply import ContentAgentApplyService
    from app.services.content_agent_jobs import ACTIVE_STATUSES, ContentAgentJobService
    identity = import_identity or _import_identity(artifact, pins, new_revision=False)
    config = ContentAgentJobCreate(levels=list(dict.fromkeys(course["level"] for course in artifact["courses"])), sources=[pin["source_name"] for pin in pins], source_ids=[pin["snapshot_id"] for pin in pins], pinned_snapshots=[{**pin, "source_id": pin["source_name"], "enabled": True} for pin in pins], apply_on_success=False)
    try:
        async with AsyncSessionLocal() as db, db.begin():
            job, created = await ContentAgentJobService.get_or_create_import_job(
                db, import_identity=identity, config=config
            )
            if not created:
                if job.status == "completed":
                    values = job.created_entity_ids.get(
                        "course_ids", job.created_entity_ids.get("courses", [])
                    )
                    return str(job.id), [str(value) for value in values], "replayed"
                if job.status in ACTIVE_STATUSES:
                    return str(job.id), [], "active"
                raise ImportValidationError(
                    f"import identity is in conflicting {job.status} state"
                )
            await ContentAgentJobService.transition(db, job, "validating", percent=90)
            await ContentAgentJobService.set_preview(db, job, artifact=artifact, source_manifest=pins, warnings=[], blocking_errors=[])
            applied_job, course_ids = await ContentAgentApplyService.apply(db, job.id)
            return str(applied_job.id), [str(value) for value in course_ids], "applied"
    finally:
        await engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate or draft-import a local course-artifact-v2 JSON against the repository approval register.")
    parser.add_argument("--artifact", required=True, help="Repository-local, non-symlink course-artifact-v2 JSON path")
    parser.add_argument("--apply", action="store_true", help="Create a draft job after all trust checks")
    database_target = parser.add_mutually_exclusive_group()
    database_target.add_argument("--local-database", action="store_true", help="Acknowledge the dedicated local development database boundary")
    database_target.add_argument("--compose-local", action="store_true", help="Acknowledge the exact local Compose PostgreSQL development boundary")
    parser.add_argument("--new-revision", action="store_true", help="Use the explicit, deterministic next approved-import identity")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        register_path = _local_json_path(str(_REGISTER_PATH), "repository source register", root=_REPOSITORY_ROOT)
        artifact_path = _local_json_path(args.artifact, "artifact", root=_REPOSITORY_ROOT)
        register, _ = _read_json_bytes(register_path, "repository source register", _MAX_REGISTER_BYTES)
        artifact, artifact_bytes = _read_json_bytes(artifact_path, "artifact", _MAX_ARTIFACT_BYTES)
        pins = _validate_register(artifact, register)
        metrics = _validate_artifact(artifact, pins)
        identity = _import_identity(artifact, pins, new_revision=args.new_revision)
        print(f"validated artifact_sha256={hashlib.sha256(artifact_bytes).hexdigest()} source_count={len(pins)} " + " ".join(f"{name}={value}" for name, value in sorted(metrics.items())))
        print(f"import_identity={identity}")
        print("raw_checksums=" + ",".join(sorted({str(pin["raw_checksum"]) for pin in pins})))
        if not args.apply:
            print("dry_run=true writes=0")
            return 0
        if not args.local_database and not args.compose_local:
            raise ImportValidationError(
                "--apply requires --local-database or --compose-local"
            )
        if args.compose_local:
            _require_compose_local_database()
        else:
            _require_local_database()
        outcome = asyncio.run(
            _apply(artifact, pins, import_identity=identity)
            if args.new_revision
            else _apply(artifact, pins)
        )
        # Retain compatibility with simple test doubles written before replay
        # outcomes were exposed.
        job_id, course_ids = outcome[0], outcome[1]
        state = outcome[2] if len(outcome) == 3 else "applied"
        print(
            f"{state} job_id={job_id} course_count={len(course_ids)} "
            f"course_ids={','.join(course_ids)} draft=true"
        )
        return 0
    except ImportValidationError as exc:
        print(f"import rejected: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"import failed without applying content: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
