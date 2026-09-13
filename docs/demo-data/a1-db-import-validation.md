# A1 database import validation

Status: **PASS — import completed, idempotency verified, and service-layer course read validated**

Run date: 2026-09-12 (Asia/Saigon)

## Scope and preflight

Immutable input: `backend-service/data/approved/a1-everyday-communication/course-artifact-v2.json`.
SHA-256: `49dcc1c2f464ecf0cf0ec1c98c59036d442659fc31260604b214f5af793fcc33`.
Import identity: `9f52b74832b4b7e234842c0f11e70f0443d00385017832fcb6a3be72af0ee490`.

Target SQLite database: `backend-service/.local-dev/lexilingo-importer.sqlite3` (size: 1,556,480 bytes starting, 71 tables, regular non-symlink file confirmed local to workspace).
Preflight verification confirmed the database had starting counts:
- `courses`: 0
- `units`: 0
- `lessons`: 0
- `vocabulary_items`: 0
- `content_agent_jobs`: 0

The prior backup database remains untouched at `backend-service/.local-dev/lexilingo-importer.alembic-failed-preflight.sqlite3`.

## Exact commands and outcomes

Environment settings:
- `APP_ENV=development`
- `DATABASE_URL=sqlite+aiosqlite:///C:/Users/hoang/orca/workspaces/lexilingo-clean-v1/run-local/backend-service/.local-dev/lexilingo-importer.sqlite3`

Execution command:
```powershell
$env:APP_ENV="development"
$env:DATABASE_URL="sqlite+aiosqlite:///C:/Users/hoang/orca/workspaces/lexilingo-clean-v1/run-local/backend-service/.local-dev/lexilingo-importer.sqlite3"
python backend-service/scripts/import_approved_course_artifact.py --artifact backend-service/data/approved/a1-everyday-communication/course-artifact-v2.json --apply --local-database
python backend-service/scripts/import_approved_course_artifact.py --artifact backend-service/data/approved/a1-everyday-communication/course-artifact-v2.json --apply --local-database
```

First apply outcome:
```text
validated artifact_sha256=49dcc1c2f464ecf0cf0ec1c98c59036d442659fc31260604b214f5af793fcc33 source_count=3 course_count=1 exercise_count=90 lesson_count=9 unit_count=3 vocabulary_count=90
import_identity=9f52b74832b4b7e234842c0f11e70f0443d00385017832fcb6a3be72af0ee490
raw_checksums=81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22,9ca6d1dcb75f822fdd66617f7d9da48142ace38dd544d6ad5e2feca1674ad3fe,b0dd3c635f1c9a4fdf1490c7e5b7c48e8bbe55b652ad0c9860a95f98e10ae498
applied job_id=1ab5d023-60a4-4000-997f-a4ae077aa191 course_count=1 course_ids=f6d99bfe-652c-468c-867c-0a9eedc21464 draft=true
```

Second apply outcome (idempotency verification):
```text
validated artifact_sha256=49dcc1c2f464ecf0cf0ec1c98c59036d442659fc31260604b214f5af793fcc33 source_count=3 course_count=1 exercise_count=90 lesson_count=9 unit_count=3 vocabulary_count=90
import_identity=9f52b74832b4b7e234842c0f11e70f0443d00385017832fcb6a3be72af0ee490
raw_checksums=81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22,9ca6d1dcb75f822fdd66617f7d9da48142ace38dd544d6ad5e2feca1674ad3fe,b0dd3c635f1c9a4fdf1490c7e5b7c48e8bbe55b652ad0c9860a95f98e10ae498
replayed job_id=1ab5d023-60a4-4000-997f-a4ae077aa191 course_count=1 course_ids=f6d99bfe-652c-468c-867c-0a9eedc21464 draft=true
```

## Database state and entity counts

Read-only inspection of `backend-service/.local-dev/lexilingo-importer.sqlite3` confirms exact graph counts:
- `courses`: 1
- `units`: 3
- `lessons`: 9
- `vocabulary_items`: 90
- `exercises`: 90 (`sum(total_exercises)` = 90; total exercises across lesson content JSON = 90)
- `content_agent_jobs`: 1

Job record details:
- `job_id`: `1ab5d023-60a4-4000-997f-a4ae077aa191`
- `status`: `completed`
- `import_identity`: `9f52b74832b4b7e234842c0f11e70f0443d00385017832fcb6a3be72af0ee490`
- `created_entity_ids`: `{"course_ids": ["f6d99bfe-652c-468c-867c-0a9eedc21464"]}`

## Service-layer course read

Executed focused ORM read via `app.crud.course.CourseCRUD.get_course_with_units`:
- Course ID: `f6d99bfe-652c-468c-867c-0a9eedc21464`
- Title: `English A1 – Everyday Communication`
- Level: `A1`
- Units count: 3
- Lessons count: 9
  - Unit 0: `Everyday Connections` (3 lessons: `Greetings and Polite Responses`, `Introducing Yourself`, `Sharing Personal Information`)
  - Unit 1: `Daily Life` (3 lessons: `Daily Routine`, `Time and Schedules`, `Home and Work`)
  - Unit 2: `Food, Shopping, and Plans` (3 lessons: `Food and Drinks`, `Shopping`, `Making Simple Plans`)

## Acceptance results

| Check | Result |
|---|---|
| Target database preflight (workspace-local, regular file, non-symlink) | **Pass** |
| Certified artifact SHA-256 / import identity validation | **Pass** |
| URL security guard validation | **Pass** (accepts `sqlite+aiosqlite:///...`) |
| First apply execution | **Pass** (`applied job_id=1ab5d023-60a4-4000-997f-a4ae077aa191`) |
| Second identical apply / idempotency | **Pass** (`replayed job_id=1ab5d023-60a4-4000-997f-a4ae077aa191`) |
| Required imported graph counts | **Pass** (1 course, 3 units, 9 lessons, 90 vocabulary records, 90 exercises, 1 completed job) |
| Stable course ID & job completion | **Pass** (`f6d99bfe-652c-468c-867c-0a9eedc21464`, `completed`) |
| Service-layer course read (`app.crud.course`) | **Pass** (Course read with 3 units and 9 lessons) |
| Service left running | **No** |

No repository application or test code was modified under this task's ownership boundary. Mutated files: `backend-service/.local-dev/lexilingo-importer.sqlite3` and `docs/demo-data/a1-db-import-validation.md`.
