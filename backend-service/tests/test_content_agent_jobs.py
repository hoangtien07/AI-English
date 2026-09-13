import hashlib
import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.content_agent import ContentAgentJob, ContentAgentUpload
from app.schemas.content_agent import ContentAgentJobCreate
from app.services.content_agent_jobs import ContentAgentJobService, request_hash


@pytest.fixture
async def content_agent_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[
                    ContentAgentUpload.__table__,
                    ContentAgentJob.__table__,
                ],
            )
        )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_duplicate_active_job_requires_revision(content_agent_db):
    config = ContentAgentJobCreate(levels=["A1"], sources=["existing_cefr"])
    requester = uuid.uuid4()

    first = await ContentAgentJobService.create(
        content_agent_db,
        requested_by_id=requester,
        config=config,
    )
    await content_agent_db.commit()

    with pytest.raises(ValueError, match="active job"):
        await ContentAgentJobService.create(
            content_agent_db,
            requested_by_id=requester,
            config=config,
        )

    revised = await ContentAgentJobService.create(
        content_agent_db,
        requested_by_id=requester,
        config=config.model_copy(update={"revision": True}),
    )

    assert first.revision == 1
    assert revised.revision == 2


async def test_job_state_machine_rejects_skipped_stages(content_agent_db):
    job = await ContentAgentJobService.create(
        content_agent_db,
        requested_by_id=uuid.uuid4(),
        config=ContentAgentJobCreate(levels=["A1"], sources=["existing_cefr"]),
    )

    with pytest.raises(ValueError, match="Invalid job transition"):
        await ContentAgentJobService.transition(
            content_agent_db, job, "generating"
        )


async def test_approved_import_lifecycle_requires_validation_before_preview(
    content_agent_db,
):
    standard_job = await ContentAgentJobService.create(
        content_agent_db,
        requested_by_id=uuid.uuid4(),
        config=ContentAgentJobCreate(levels=["A1"], sources=["existing_cefr"]),
    )
    with pytest.raises(ValueError, match="Invalid job transition: queued -> validating"):
        await ContentAgentJobService.transition(content_agent_db, standard_job, "validating")

    job, created = await ContentAgentJobService.get_or_create_import_job(
        content_agent_db,
        import_identity="a" * 64,
        config=ContentAgentJobCreate(levels=["A1"], sources=["existing_cefr"]),
    )
    assert created is True

    # Invalid skipped transitions from queued remain rejected
    with pytest.raises(ValueError, match="Invalid job transition: queued -> preview_ready"):
        await ContentAgentJobService.set_preview(
            content_agent_db,
            job,
            artifact={},
            source_manifest=[],
            warnings=[],
            blocking_errors=[],
        )

    with pytest.raises(ValueError, match="Invalid job transition: queued -> applying"):
        await ContentAgentJobService.transition(content_agent_db, job, "applying")

    # Valid lifecycle progression: queued -> validating -> preview_ready -> applying -> completed
    await ContentAgentJobService.transition(content_agent_db, job, "validating", percent=90)
    preview = await ContentAgentJobService.set_preview(
        content_agent_db,
        job,
        artifact={"courses": []},
        source_manifest=[],
        warnings=[],
        blocking_errors=[],
    )

    assert preview.status == "preview_ready"
    assert preview.progress["percent"] == 100

    # Invalid skipped transition: preview_ready cannot skip applying to completed
    with pytest.raises(ValueError, match="Invalid job transition: preview_ready -> completed"):
        await ContentAgentJobService.transition(content_agent_db, preview, "completed")

    applying = await ContentAgentJobService.transition(content_agent_db, preview, "applying")
    assert applying.status == "applying"

    completed = await ContentAgentJobService.transition(content_agent_db, applying, "completed")
    assert completed.status == "completed"
    assert completed.completed_at is not None



def test_request_hash_changes_when_snapshot_pin_changes():
    def config(snapshot_id: str) -> ContentAgentJobCreate:
        return ContentAgentJobCreate(
            levels=["A1"],
            sources=["oewn"],
            pinned_snapshots=[
                {
                    "source_id": "oewn",
                    "source_name": "oewn",
                    "source_version": "2025",
                    "snapshot_id": snapshot_id,
                    "official_url": "https://en-word.net/static/english-wordnet-2025.xml.gz",
                    "license_id": "CC-BY-4.0",
                    "license_url": "https://creativecommons.org/licenses/by/4.0/",
                    "attribution_text": "Open English WordNet 2025",
                    "retrieved_at": "2026-06-15T00:00:00Z",
                    "raw_checksum": "a" * 64,
                    "normalized_sha256": "b" * 64,
                    "normalized_bytes": 100,
                    "record_checksum_root": "c" * 64,
                    "adapter_version": 1,
                    "record_count": 100,
                    "status": "active",
                    "enabled": True,
                }
            ],
        )

    assert request_hash(config("snapshot-a")) != request_hash(config("snapshot-b"))


def test_validate_import_identity_accepts_normalized_64_hex():
    valid = "0123456789abcdef" * 4
    assert ContentAgentJobService.validate_import_identity(valid) == valid
    all_f = "f" * 64
    assert ContentAgentJobService.validate_import_identity(all_f) == all_f


@pytest.mark.parametrize(
    "invalid_value",
    [
        "A" * 64,  # Uppercase hex rejected
        "a" * 63 + "F",  # Mixed case rejected
        "g" * 64,  # Non-hex characters
        " " * 64,  # Whitespace rejected
        "a" * 63,  # Too short (63 chars)
        "a" * 65,  # Too long (65 chars)
        "",  # Empty string
        None,  # None type
        12345,  # Integer
        ["a" * 64],  # List
        {"identity": "a" * 64},  # Dict
    ],
)
def test_validate_import_identity_rejects_invalid_values(invalid_value):
    with pytest.raises(
        ValueError, match="import identity must be a normalized 64-character hex digest"
    ):
        ContentAgentJobService.validate_import_identity(invalid_value)


async def test_get_or_create_import_job_creates_and_retrieves(content_agent_db):
    identity = "a" * 64
    config = ContentAgentJobCreate(levels=["A1"], sources=["oewn"])

    job, created = await ContentAgentJobService.get_or_create_import_job(
        content_agent_db,
        import_identity=identity,
        config=config,
    )
    await content_agent_db.commit()

    assert created is True
    assert job.import_identity == identity
    assert job.status == "queued"
    assert job.revision == 1
    assert job.requested_by_id is None
    assert job.upload_id is None
    expected_hash = hashlib.sha256(
        f"approved-artifact-import-v1:{identity}".encode("ascii")
    ).hexdigest()
    assert job.request_hash == expected_hash
    assert job.progress == {"stage": "queued", "percent": 0, "counters": {}}

    # Second retrieval with exact identity returns the existing job without creating a new one
    job2, created2 = await ContentAgentJobService.get_or_create_import_job(
        content_agent_db,
        import_identity=identity,
        config=config,
    )
    assert created2 is False
    assert job2.id == job.id
    assert job2.import_identity == identity


async def test_get_or_create_import_job_validates_identity_before_db(content_agent_db):
    config = ContentAgentJobCreate(levels=["A1"], sources=["oewn"])
    with pytest.raises(
        ValueError, match="import identity must be a normalized 64-character hex digest"
    ):
        await ContentAgentJobService.get_or_create_import_job(
            content_agent_db,
            import_identity="invalid-identity",
            config=config,
        )


async def test_get_or_create_import_job_recovers_from_concurrent_integrity_error(
    content_agent_db, monkeypatch
):
    identity = "b" * 64
    config = ContentAgentJobCreate(levels=["A1"], sources=["oewn"])

    # Seed the job in DB so it exists
    existing_job, created = await ContentAgentJobService.get_or_create_import_job(
        content_agent_db,
        import_identity=identity,
        config=config,
    )
    await content_agent_db.commit()
    assert created is True

    # Simulate race: initial scalar check returns None, so it tries to insert,
    # raising IntegrityError on unique constraint; recovery scalar check finds existing.
    original_scalar = content_agent_db.scalar
    lookup_count = [0]

    async def race_scalar(query, *args, **kwargs):
        lookup_count[0] += 1
        if lookup_count[0] == 1:
            return None
        return await original_scalar(query, *args, **kwargs)

    monkeypatch.setattr(content_agent_db, "scalar", race_scalar)

    recovered_job, recovered_created = (
        await ContentAgentJobService.get_or_create_import_job(
            content_agent_db,
            import_identity=identity,
            config=config,
        )
    )
    assert recovered_created is False
    assert recovered_job.id == existing_job.id
    assert lookup_count[0] >= 2


async def test_get_or_create_import_job_reraises_unrelated_integrity_error(
    content_agent_db, monkeypatch
):
    identity = "c" * 64
    config = ContentAgentJobCreate(levels=["A1"], sources=["oewn"])

    async def fake_flush(*args, **kwargs):
        raise IntegrityError("simulated non-identity constraint", params=None, orig=Exception("fail"))

    monkeypatch.setattr(content_agent_db, "flush", fake_flush)

    with pytest.raises(IntegrityError, match="simulated non-identity constraint"):
        await ContentAgentJobService.get_or_create_import_job(
            content_agent_db,
            import_identity=identity,
            config=config,
        )


async def test_import_identity_unique_constraint_enforced(content_agent_db):
    identity = "d" * 64
    job1 = ContentAgentJob(
        request_hash="11" * 32,
        import_identity=identity,
        config={"levels": ["A1"], "sources": ["oewn"]},
    )
    content_agent_db.add(job1)
    await content_agent_db.commit()

    job2 = ContentAgentJob(
        request_hash="22" * 32,
        import_identity=identity,
        config={"levels": ["A1"], "sources": ["oewn"]},
    )
    content_agent_db.add(job2)
    with pytest.raises(IntegrityError):
        await content_agent_db.commit()
    await content_agent_db.rollback()


async def test_import_identity_nullable_legacy_compatibility(content_agent_db):
    # Multiple jobs with import_identity=None can coexist without violating unique constraint
    job1 = ContentAgentJob(
        request_hash="33" * 32,
        import_identity=None,
        config={"levels": ["A1"], "sources": ["oewn"]},
    )
    job2 = ContentAgentJob(
        request_hash="44" * 32,
        import_identity=None,
        config={"levels": ["A1"], "sources": ["oewn"]},
    )
    content_agent_db.add(job1)
    content_agent_db.add(job2)
    await content_agent_db.commit()

    # Standard API create sets import_identity=None
    created = await ContentAgentJobService.create(
        content_agent_db,
        requested_by_id=uuid.uuid4(),
        config=ContentAgentJobCreate(levels=["A1"], sources=["oewn"]),
    )
    assert created.import_identity is None
