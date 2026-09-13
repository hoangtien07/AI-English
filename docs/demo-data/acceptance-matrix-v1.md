# LexiLingo Demo Data Acceptance Matrix Specification (v1)

**Document Reference:** `docs/demo-data/acceptance-matrix-v1.md`  
**Execution Context:** WAVE A3 — Demo Data Acceptance Matrix  
**Target Repository:** `C:\Users\hoang\orca\workspaces\lexilingo-clean-v1\run-local`  
**Author / Engine:** Antigravity 3.8 Flash (Dispatched Worker `task_0d111e652996` / Context `ctx_687afb9d7a0e`)  
**Status:** Canonical Acceptance Matrix & Quality Gate Reference (Document-Only / Read-Only Analysis)  
**Date:** 2026-09-10  

---

## 1. Executive Summary & Governance Framework

### 1.1 Purpose & Scope
This document defines the definitive, measurable pass/fail acceptance criteria for the LexiLingo / AI-English **Demo Data Pack v1**. It provides strict quality gates governing data provenance, contract schema validation, execution dry-runs, operational idempotency, relational referential integrity, duplicate prevention, persona namespace isolation, end-to-end user journeys, automated test suites, rollback recovery, and explicit blocked conditions.

This specification builds upon and unifies the findings of:
1. [`docs/demo-data/source-inventory-v1.md`](source-inventory-v1.md) (Wave A1: Inventory of content sources, licenses, and dispositions)
2. [`docs/demo-data/schema-mapping-v1.md`](schema-mapping-v1.md) (Wave A2: End-to-end contract, ETL, ORM, and database mapping)
3. [`docs/INDEPENDENT_DEVELOPMENT_PLAN.md`](../INDEPENDENT_DEVELOPMENT_PLAN.md) (Governance, zero-network, and clean independent ownership)
4. [`docs/LOCAL_PARITY_JOURNEY_LEDGER.md`](../LOCAL_PARITY_JOURNEY_LEDGER.md) (Local user journey parity ledger and status gates)
5. [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json) (Machine-readable provenance catalog)

### 1.2 Core Architectural Principles
* **Measurable Pass/Fail Verifiability:** Every gate must be deterministically verifiable using observable command output, exit codes, database row counts, or structural assertions.
* **Evidence-Backed Commands:** Commands are extracted directly from checked-in repository scripts, tests, and configuration. Any operation requiring functionality not yet present in the codebase is explicitly labeled `TBD`.
* **Zero Network Dependency:** Local demo workflows must never make outbound network calls to external APIs, news feeds, cloud databases, or original author endpoints (`api.lexilingo.me`, `ai.lexilingo.me`, `lexilingo-88492`).
* **Fail-Closed Security & Licensing:** In the absence of an explicit, written rights record or approved allowlist entry, ingestion and distribution are blocked.
* **Preservation of Curated Data:** Synthetic demo pipelines and automated re-seeding must never overwrite human-authored learning content or real user data.

---

## 2. Master Acceptance Matrix Overview

The matrix below summarizes the 11 quality dimensions, their primary enforcement mechanisms, and their verification gates:

| Dimension | Primary Guard / Mechanism | Core Verification Target | Pass Standard | Failure Impact |
|---|---|---|---|---|
| **1. Provenance** | `LOCAL_DATA_PROVENANCE_MANIFEST.json`, `content_provenance` | Licenses, attribution, hashes | 100% manifest and allowlist compliance | Fatal halt; unverified content quarantined |
| **2. Schema Validation** | `validate_artifact`, JSON Schemas | Pydantic contracts, JSON shapes, enums | Zero schema or enum violations | Rejection at intake boundary before DB I/O |
| **3. Dry-Run** | In-memory validation, `import_course_content.py --file` | Zero persistent mutations | Delta = 0 rows in DB; validation passes | Unintended DB pollution; unhandled schema errors |
| **4. Idempotency** | Alembic migrations, upsert keys, namespace wipes | Repeated script execution | `Count(Run_1) == Count(Run_N)` | Fatal unique violations, ballooning tables |
| **5. Referential Integrity** | Postgres foreign keys, cascade rules | Relational hierarchy | Zero orphaned records; clean cascades | Relational integrity errors; broken UX |
| **6. Duplicate Prevention** | `(word, part_of_speech)`, unique indexes | Vocabulary, users, categories | Unique constraints satisfied; canonical normalization | Data corruption; ambiguous dictionary lookups |
| **7. Persona Isolation** | Email namespace partitions, `random.seed(42)` | User accounts, activity history | Zero personal data; synthetic namespaces only | Privacy breach; developer credential leakage |
| **8. UI Journeys** | Flutter Web client, Admin Dashboard | Learning roadmap, shop, analytics | All playable nodes launch; admin KPIs render | 409 Conflict; blank screens; unplayable lessons |
| **9. Tests** | Pytest, Ruff, Flutter test, Pester | Code quality, contracts, parity | 100% passing automated suites | Blocked CI/CD; regression escape |
| **10. Rollback** | AsyncSession rollback, Alembic downgrade | Atomic transactions, Docker tags | Immediate revert to prior consistent state | Partial course writes; inconsistent DB |
| **11. Blocked Conditions** | Security sentinels, fail-closed guards | Crawlers, personal data, cloud URLs | Immediate abort if blocked pattern detected | Build rejection; security/copyright violation |

---

## 3. Dimension 1: Data Provenance & Licensing

### 3.1 Context & Objectives
Demonstrate that all ingested content, test fixtures, and catalog items possess verified origin records, valid open licenses, non-empty attributions, and immutable cryptographic digests. Disallow inferring content rights from software licenses ([`LICENSE`](../../LICENSE)).

### 3.2 Measurable Pass/Fail Criteria

| Check ID | Requirement | Target Entity / Artifact | Measurable Condition (Pass Criteria) | Failure Condition (Fail Criteria) | Verification Method & Command |
|---|---|---|---|---|---|
| **PRV-01** | Provenance Manifest Schema Conformance | [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json) | File passes structural validation: `schema_version == 1`, unique IDs, valid foreign keys, and all paths resolve locally. | File missing, invalid JSON, unmapped foreign keys, or non-resolving paths. | `python -m pytest docs/tests/test_local_data_provenance_manifest.py -q` |
| **PRV-02** | Mandatory Provenance Header in Course Artifact | Course Artifact v2 (`ContentAgentArtifact`) | `source_manifest` contains at least 1 entry with valid `snapshot_id`, `raw_checksum`, `record_checksum_root`, `license_id`, and `attribution_text`. | Missing `source_manifest`, empty array, or missing cryptographic checksums. | `pytest backend-service/tests/test_content_agent_validation.py -k test_manifest -q` |
| **PRV-03** | License Allowlist Adherence | `ArtifactSourceManifest.license_id` | `license_id` is an exact member of approved set: `{"CC0-1.0", "CC-BY-2.0-FR", "CC-BY-4.0", "LicenseRef-CMUdict", "LicenseRef-CEFR-J-Commercial", "LicenseRef-Admin-Owned", "LicenseRef-Generated"}`. | `license_id` is null, unapproved (e.g. unpinned commercial CEFR-J), or proprietary without written agreement. | `pytest backend-service/tests/test_content_agent_validation.py -k test_license_mode -q` |
| **PRV-04** | SHA-256 Digest Immutability | Manifest & Artifact Checksums | All `raw_checksum` and `record_checksum` fields match regex `^[a-f0-9]{64}$` and recompute identically from source payloads. | Checksum missing, malformed length, uppercase hex, or failing verification hash. | `pytest backend-service/tests/test_content_agent_validation.py -k test_manifest -q` |
| **PRV-05** | Database Provenance Relational Persistence | Table `content_provenance` ([`backend-service/app/models/content_agent.py`](../../backend-service/app/models/content_agent.py)) | Row created for applied course (`entity_type='course'`) and every applied vocabulary word (`entity_type='vocabulary'`) linking to `job_id`. | Course or vocabulary created without corresponding `content_provenance` row. | `pytest backend-service/tests/test_content_agent_apply.py -q` |
| **PRV-06** | Quarantine of Unverified Repository Datasets | Unverified Files: [`scripts/categorized_words_final.json`](../../scripts/categorized_words_final.json), [`ai-service/data/sample_stories.json`](../../ai-service/data/sample_stories.json), [`ai-service/data/kg/*.json`](../../ai-service/data/kg) | Unverified files are marked `hold_pending_rights` and excluded from default seed entrypoints. | Ingesting unverified files into standard demo seed without an approved provenance manifest. | `python -m pytest docs/tests/test_local_data_provenance_manifest.py -q` |

---

## 4. Dimension 2: Contract & Schema Validation

### 4.1 Context & Objectives
Ensure that all course, lesson, exercise, and vocabulary data models strictly satisfy their formal JSON Schema contracts, Pydantic validation rules, and relational column constraints before reaching persistence.

### 4.2 Measurable Pass/Fail Criteria

| Check ID | Requirement | Target Entity / Artifact | Measurable Condition (Pass Criteria) | Failure Condition (Fail Criteria) | Verification Method & Command |
|---|---|---|---|---|---|
| **SCH-01** | JSON Schema Draft 2020-12 Validation | [`contracts/content-agent/course-artifact-v2.schema.json`](../../contracts/content-agent/course-artifact-v2.schema.json) | Course generation artifact conforms strictly to JSON Schema draft 2020-12 without schema errors. | Missing required properties, additional unauthorized properties, or invalid types. | `pytest backend-service/tests/test_content_agent_contract.py -q` |
| **SCH-02** | CEFR Level Enumeration Integrity | `Course.level`, `VocabularyItem.difficulty_level` | Level string is strictly one of `{"A1", "A2", "B1", "B2", "C1", "C2"}` (case-sensitive uppercase). | Values such as `"a1"`, `"beginner"`, `"B3"`, or null in required level fields. | `pytest backend-service/tests/test_content_agent_validation.py -k test_cefr -q` |
| **SCH-03** | Part-of-Speech Enumeration Integrity | `VocabularyItem.part_of_speech` | Value matches lowercase enum: `{"noun", "verb", "adjective", "adverb", "pronoun", "preposition", "conjunction", "interjection", "phrase"}`. | Uppercase values (e.g. `"NOUN"`), legacy abbreviations (`"n."`), or unrecognized grammatical tags. | `pytest backend-service/tests/test_content_agent_validation.py -k test_pos -q` |
| **SCH-04** | Exercise UI Type to Engine Base Type Mapping | `lessons.content["exercises"]` | Every exercise `ui_type` resolves to a valid base `type` via `UI_TYPE_TO_BASE_TYPE` ([`backend-service/app/models/course.py`](../../backend-service/app/models/course.py)). | `ui_type` unmapped, base `type` invalid, or widget unsupported by mobile/web renderers. | `pytest backend-service/tests/test_content_agent_validation.py -k test_exercise_type -q` |
| **SCH-05** | Pair / Matching Exercise Syntax | Exercises of type `matching`, `match_word_to_meaning` | `options` contains all keys followed by all values; `correct_answer` is formatted as `"key1:value1, key2:value2"` separated strictly by `", "`. | Using pipe separators (`"|"`), omitting comma-space, or passing unaligned pairs. | `pytest backend-service/tests/test_audit_course_repair.py -q` |
| **SCH-06** | Sentence Rearrangement Tile Syntax | Exercises of type `reorder`, `arrange_the_sentence` | `options` contains shuffled word tiles; `correct_answer` is the complete sentence; answer is NOT an option element. | Answer included directly in option tiles or shuffled tiles missing target tokens. | `pytest backend-service/tests/test_audit_course_repair.py -q` |
| **SCH-07** | Text Prompt for Audio Exercises | Listening / Speaking Exercises | `question` field is non-empty string whenever `audio_url` is populated. | Empty `question` prompt on audio exercise causing blank UI render. | `pytest backend-service/tests/test_content_agent_validation.py -k test_audio -q` |
| **SCH-08** | Database String Length Bounds | Relational Columns | `pronunciation <= 100` chars; `audio_url <= 500` chars; `title <= 255` chars; `word <= 255` chars. | Strings exceeding database column bounds causing unhandled SQL `DataError`. | `pytest backend-service/tests/test_content_agent_contract.py -k vocabulary_normalization -q` |

---

## 5. Dimension 3: Dry-Run & Non-Mutating Verification

### 5.1 Context & Objectives
Guarantee that validation, inspection, and verification utilities can execute without side effects, without opening mutating database connections, and without writing residual records when run in preview or dry-run mode.

### 5.2 Measurable Pass/Fail Criteria

| Check ID | Requirement | Target Entity / Artifact | Measurable Condition (Pass Criteria) | Failure Condition (Fail Criteria) | Verification Method & Command |
|---|---|---|---|---|---|
| **DRY-01** | Pure In-Memory Boundary Validation | [`backend-service/app/services/content_agent_validation.py`](../../backend-service/app/services/content_agent_validation.py) | Function `validate_artifact(artifact)` runs purely in-memory; performs 0 database calls; returns boolean `is_valid` and error list. | Validation function requires live DB session, connects to network, or throws unhandled I/O errors. | `pytest backend-service/tests/test_content_agent_validation.py -q` |
| **DRY-02** | Course Importer Transactional Dry-Run | [`backend-service/scripts/import_course_content.py`](../../backend-service/scripts/import_course_content.py) | Running script without `--apply` executes SQL statements inside `conn.transaction()`, verifies schema casts, and rolls back via `asyncio.CancelledError`. | Dry-run persists rows to database, or skips SQL execution entirely (failing to test column casts). | `python backend-service/scripts/import_course_content.py --file <file>` (TBD: requires input dump) |
| **DRY-03** | Zero Database Delta Post Dry-Run | Target Database Tables (`courses`, `units`, `lessons`) | Total row count delta across all tables is strictly 0: `Count_post - Count_pre == 0`. | Row count increases or decreases after a dry-run execution. | Pre/post SQL query: `SELECT count(*) FROM courses;` (Delta must be 0) |
| **DRY-04** | Content Agent Job Preview State | Table `content_agent_jobs` | Artifact creation transitions job to `preview_ready`; application to relational tables requires explicit subsequent `/apply` action. | Job automatically mutates relational course tables during preview generation without review. | `pytest backend-service/tests/test_content_agent_jobs.py -k test_preview -q` |
| **DRY-05** | Demo Data Seed Dry-Run Capability | Seed Scripts: `seed_shop_items.py`, `seed_demo_data.py`, `seed_analytics.py` | Ability to preview seed record counts without committing changes. | Scripts immediately write to database without dry-run confirmation mode. | **TBD** (Currently requires running in isolated scratch DB via `python -m scripts.run_isolated_tests`) |

---

## 6. Dimension 4: Operational Idempotency

### 6.1 Context & Objectives
Demonstrate that running bootstrap, seed, or import processes repeatedly on the same environment produces identical final state without raising unique constraint violations, corrupting existing records, or multiplying row counts.

### 6.2 Measurable Pass/Fail Criteria

| Check ID | Requirement | Target Entity / Artifact | Measurable Condition (Pass Criteria) | Failure Condition (Fail Criteria) | Verification Method & Command |
|---|---|---|---|---|---|
| **IDM-01** | Alembic Schema Migration Idempotency | [`backend-service/scripts/bootstrap_local.py`](../../backend-service/scripts/bootstrap_local.py) | Re-running migration command reports database is up-to-date; exit code is 0; schema remains intact. | Migration script fails on re-run, attempts duplicate table creation, or throws DDL error. | `python backend-service/scripts/bootstrap_local.py` |
| **IDM-02** | Shop Catalog Seeding Idempotency | [`backend-service/scripts/seed_shop_items.py`](../../backend-service/scripts/seed_shop_items.py) | First run creates 54 items; second run creates 0 items and updates 54 items; total count remains exactly 54. | Second run creates duplicate items or raises `IntegrityError` on unique name constraint. | Run script twice sequentially: `python backend-service/scripts/seed_shop_items.py` |
| **IDM-03** | Direct Sample Course Seeding Idempotency (Uncataloged Artifact) | [`backend-service/scripts/seed_courses_directly.py`](../../backend-service/scripts/seed_courses_directly.py) | Re-running script replaces existing course by `title` via cascade delete/recreate; achievement and category counts remain constant. Note: `sample_data_catalog.py` is not cataloged in `LOCAL_DATA_PROVENANCE_MANIFEST.json` and is classified fail-closed (`hold_pending_rights`). | Re-running script produces duplicate courses or foreign key collision. | **BLOCKED:** do not execute until the exact artifact is approved in the tracked provenance manifest; then run twice only against an isolated database. |
| **IDM-04** | Vocabulary Batch Catalog Upsert Idempotency | Function `upsert_vocabulary_batch` ([`backend-service/app/services/vocabulary_catalog.py`](../../backend-service/app/services/vocabulary_catalog.py)) | Repeated ingestion of same word and part-of-speech returns existing UUID; does not duplicate row; preserves existing curated definition. | Duplicate row created; unique constraint violated; or human-curated definition overwritten by automated text. | `pytest backend-service/tests/test_content_agent_apply.py -k idempotent -q` |
| **IDM-05** | Synthetic Persona Reseed Idempotency | [`backend-service/scripts/seed_demo_data.py`](../../backend-service/scripts/seed_demo_data.py) | Startup cleanup wipes `demo_%@lexilingo.dev`; reseeds fresh 45 accounts; total demo users after 2 runs equals exactly 45. | Demo user count doubles to 90 on second run, or orphaned activities remain. | Run script twice sequentially: `python backend-service/scripts/seed_demo_data.py` |
| **IDM-06** | Course Content Importer Idempotency | [`backend-service/scripts/import_course_content.py`](../../backend-service/scripts/import_course_content.py) | Rows keyed by UUID are handled via `ON CONFLICT (id) DO NOTHING`; second run reports `skipped == total_rows`. | Second run attempts duplicate insert or fails with primary key violation. | Run import script twice with `--apply`: `python backend-service/scripts/import_course_content.py --file <file> --apply` |

---

## 7. Dimension 5: Relational Referential Integrity

### 7.1 Context & Objectives
Ensure all database foreign key relationships, cascade deletion rules, and junction table linkages remain complete, consistent, and free of dangling or orphaned references.

### 7.2 Measurable Pass/Fail Criteria

| Check ID | Requirement | Target Entity / Artifact | Measurable Condition (Pass Criteria) | Failure Condition (Fail Criteria) | Verification Method & Command |
|---|---|---|---|---|---|
| **REF-01** | Course-to-Unit Cascade Integrity | `units.course_id` -> `courses.id` | Foreign key defined with `ondelete="CASCADE"`; deleting a course deletes all associated units automatically. | Deleting a course fails with foreign key violation, or leaves orphaned units in database. | `pytest backend-service/tests/test_content_agent_apply.py -q; inspection of ondelete="CASCADE" on units.course_id in backend-service/app/models/course.py` |
| **REF-02** | Unit-to-Lesson Cascade Integrity | `lessons.unit_id` -> `units.id` | Foreign key defined with `ondelete="CASCADE"`; deleting a unit deletes all associated lessons automatically. | Orphaned lessons remain with dangling `unit_id`. | `pytest backend-service/tests/test_content_agent_apply.py -q; inspection of ondelete="CASCADE" on lessons.unit_id in backend-service/app/models/course.py` |
| **REF-03** | Lesson-to-Vocabulary Junction Integrity | Table `lesson_vocabulary_items` ([`backend-service/app/models/content_agent.py`](../../backend-service/app/models/content_agent.py)) | Foreign keys `lesson_id` -> `lessons.id` and `vocabulary_id` -> `vocabulary_items.id` resolve to existing parent rows; cascading enabled. | Dangling foreign key references in junction table after lesson or vocabulary removal. | `pytest backend-service/tests/test_content_agent_apply.py -q; inspection of ForeignKey CASCADE in backend-service/app/models/content_agent.py` |
| **REF-04** | Content Provenance Job Association | `content_provenance.job_id` -> `content_agent_jobs.id` | Every row in `content_provenance` references a valid `job_id` (`ondelete="CASCADE"`). | Orphaned provenance records referencing non-existent job UUIDs. | `pytest backend-service/tests/test_content_agent_apply.py -q; inspection of ForeignKey CASCADE in backend-service/app/models/content_agent.py` |
| **REF-05** | Course Category Foreign Key | `courses.category_id` -> `course_categories.id` | `category_id` is either null or resolves to a valid row in `course_categories`. | Non-null `category_id` references non-existent category UUID. | `python backend-service/scripts/audit_course_content.py` |
| **REF-06** | User Activity Cascade Integrity | Progress & Gamification Tables | Deleting a synthetic user deletes all linked `daily_activities`, `user_course_progress`, `lesson_completions`, `user_vocabulary`, `streaks`, `user_wallets`. | Orphaned activity rows or progress records remaining after user deletion. | SQL query: `SELECT count(*) FROM daily_activities da LEFT JOIN users u ON da.user_id = u.id WHERE u.id IS NULL;` (Must return 0) |

---

## 8. Dimension 6: Duplicate Prevention

### 8.1 Context & Objectives
Enforce uniqueness at database schema, application domain, and data normalization layers to prevent semantic or physical duplicates across dictionary items, course structures, and user accounts.

### 8.2 Measurable Pass/Fail Criteria

| Check ID | Requirement | Target Entity / Artifact | Measurable Condition (Pass Criteria) | Failure Condition (Fail Criteria) | Verification Method & Command |
|---|---|---|---|---|---|
| **DUP-01** | Lexical Word Normalization & Uniqueness | Table `vocabulary_items` | Words are canonicalized via `normalize_word` (NFKC Unicode normalization, lowercased, punctuation stripped, whitespace collapsed). Part of unique constraint `(word, part_of_speech)`. | Storing duplicate entries differing only by case (e.g. `"Run"` vs `"run"`) or trailing spaces. | `pytest backend-service/tests/test_content_contract_parity.py -q` |
| **DUP-02** | Lesson-Vocabulary Pair Uniqueness | Table `lesson_vocabulary_items` | Unique constraint enforced on `(lesson_id, vocabulary_id)`; a vocabulary word is linked to a given lesson at most once. | Duplicate rows linking same vocabulary word to same lesson multiple times. | `pytest backend-service/tests/test_content_agent_apply.py -k deduplicates -q` |
| **DUP-03** | User Account Uniqueness | Table `users` | Unique constraint on `users.email`; attempts to create duplicate email rejected at database level. | Duplicate user records with identical email address. | `pytest backend-service/tests/test_auth_routes.py -q; UniqueConstraint on users.email in backend-service/app/models/user.py` |
| **DUP-04** | Course Category Slug Uniqueness | Table `course_categories` | Unique constraint on `course_categories.slug`. | Duplicate category slugs causing ambiguous category routing. | Verified by `admin_seed_service.seed_course_categories` |
| **DUP-05** | Shop Item & Achievement Uniqueness | Tables `shop_items`, `achievements` | Unique index on `shop_items.name` and `achievements.name`. | Duplicate powerup or achievement entries in catalog. | Verified by `seed_shop_items.py` and `admin_seed_service.seed_achievements` |
| **DUP-06** | Exercise Identification Uniqueness | Lesson Exercise Array | Every exercise in `lessons.content["exercises"]` has a unique `id` across the artifact. | Duplicate exercise `id`s causing state collision in frontend widget keys. | `pytest backend-service/tests/test_content_agent_validation.py -k duplicate_exercise_id -q` |

---

## 9. Dimension 7: Persona Isolation & Privacy Safeguards

### 9.1 Context & Objectives
Ensure absolute segregation between synthetic demo personas, test accounts, real users, and prohibited developer personal credentials, complying with [`docs/INDEPENDENT_DEVELOPMENT_PLAN.md`](../INDEPENDENT_DEVELOPMENT_PLAN.md) Section 3.1.

### 9.2 Measurable Pass/Fail Criteria

| Check ID | Requirement | Target Entity / Artifact | Measurable Condition (Pass Criteria) | Failure Condition (Fail Criteria) | Verification Method & Command |
|---|---|---|---|---|---|
| **ISO-01** | Synthetic Demo Persona Namespace Confinement | [`backend-service/scripts/seed_demo_data.py`](../../backend-service/scripts/seed_demo_data.py) | All seeded demo user accounts strictly match email pattern `demo_%@lexilingo.dev`. | Script creates users outside designated `demo_%@lexilingo.dev` domain. | SQL query: `SELECT count(*) FROM users WHERE email NOT LIKE 'demo_%@lexilingo.dev' AND email LIKE '%demo%';` |
| **ISO-02** | Synthetic Analytics Namespace Confinement | [`backend-service/scripts/seed_analytics.py`](../../backend-service/scripts/seed_analytics.py) | All seeded analytics test users strictly match `@lexilingo.test` or `admin*@lexilingo.dev`. | Script seeds accounts in production or unapproved domains. | SQL query: `SELECT DISTINCT split_part(email, '@', 2) FROM users;` |
| **ISO-03** | Deterministic Persona Randomness | [`backend-service/scripts/seed_analytics.py`](../../backend-service/scripts/seed_analytics.py) | Script initializes random generator with fixed seed: `random.seed(42)`; re-running produces bit-identical user metrics. | Unseeded random generation causing nondeterministic analytics dashboards. | Code inspection: line 52 in `seed_analytics.py` |
| **ISO-04** | Scoped Teardown Boundary | Seed Script Startup Cleanup | Scoped delete operations remove ONLY accounts matching their respective synthetic namespaces (`demo_%@lexilingo.dev` or `@lexilingo.test`). Real users and reference catalogs are untouched. | Deleting real learner accounts, OAuth profiles, courses, or shop items during demo reset. | Code inspection: `seed_demo_data.py` (lines 11-16) and `seed_analytics.py` (lines 11-16) |
| **ISO-05** | Complete Exclusion of Developer Personal Data | Prohibited Files: [`seed_nhthang.py`](../../backend-service/scripts/seed_nhthang.py), [`seed_proficiency_data.py`](../../backend-service/scripts/seed_proficiency_data.py) | Zero records containing `nhthang312@gmail.com` exist in the database; scripts are never executed in demo setup. | Personal email `nhthang312@gmail.com` found in `users` table or database dumps. | SQL query: `SELECT count(*) FROM users WHERE email = 'nhthang312@gmail.com';` (Must return 0) |
| **ISO-06** | Super-Admin Exact Allowlist | Super-Admin Privilege Assignment | Elevated roles granted solely to owner-approved exact super-admin email; no automatic domain wildcards. | Auto-elevating arbitrary accounts or granting admin rights based on domain regex. | `python scripts/security/verify_independent_config.py` |

---

## 10. Dimension 8: UI Journeys & Functional Parity

### 10.1 Context & Objectives
Validate the core learner and administrative user journeys defined in [`docs/LOCAL_PARITY_JOURNEY_LEDGER.md`](../LOCAL_PARITY_JOURNEY_LEDGER.md), ensuring that seeded data enables interactive, error-free UI workflows.

### 10.2 Measurable Pass/Fail Criteria

| Check ID | Journey ID | Target Surface / Route | Measurable Condition (Pass Criteria) | Failure Condition (Fail Criteria) | Verification Method & Command |
|---|---|---|---|---|---|
| **UIJ-01** | `J-01` | Database Bootstrap & Restart | Empty DB bootstraps via `bootstrap_local.py`; survives Postgres container restart; retains Alembic head version. | Restart causes table loss, migration failure, or missing schema extensions. | `python backend-service/scripts/bootstrap_local.py` followed by container restart |
| **UIJ-02** | `J-02` | Shop Catalog Browsing | Flutter shop screen renders 54 items (18 consumable powerups, 36 avatar items) with gem prices and icons. | Shop screen shows blank list, missing icons, or unhandled null pricing. | `.\scripts\dev-local.ps1 up-core` then verify `GET /api/v1/shop/items` returns 54 items |
| **UIJ-03** | `J-03` | Admin Analytics Dashboard | Admin dashboard displays KPI widgets, 90-day user growth, DAU/WAU/MAU, and completion funnel from synthetic data. | Empty graphs, division-by-zero errors, or 500 Internal Server Error on analytics endpoints. | `GET /admin/analytics/dashboard/kpis` returns HTTP 200 with non-zero metrics |
| **UIJ-04** | `J-04` | Course Learning Roadmap | Flutter learning roadmap ([`learning_roadmap_screen.dart`](../../flutter-app/lib/features/learning/presentation/screens/learning_roadmap_screen.dart)) renders 2 A1 courses; tapping lesson opens exercises without 409 Conflict. | **UNVERIFIED / HELD**: `sample_data_catalog.py` is not cataloged in [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json); learning path journey remains unverified pending owner rights approval of an authorized local content pack. | `python backend-service/scripts/audit_course_content.py` confirms 0 unplayable lessons |
| **UIJ-05** | `J-05` | AI Story Conversation | Story role-play interface initiates dialogue turn; SSE stream delivers assistant response. | **UNVERIFIED / HELD**: Quarantined until rights decision on [`sample_stories.json`](../../ai-service/data/sample_stories.json). | Journey J-05 gate: blocked until provenance approval |
| **UIJ-06** | `J-06` | Voice & STT Interaction | Learner speaks prompt; Moonshine/Faster-Whisper STT transcribes utterance; Piper TTS speaks audio; latency < 2.0s. | Audio transcribe timeout, empty transcription, or unhandled audio codec error. | Focused AI STT gate tests: `138 worker + 15 gate tests passed` |
| **UIJ-07** | `J-07` | External RSS Lesson Crawl | Live RSS news feed transformed into interactive lesson. | **INTENTIONALLY_DISABLED**: External crawling prohibited. | Blocked under governance directive |
| **UIJ-08** | `J-08` | External Anki Deck Import | Ingestion of external `.apkg` vocabulary package. | **INTENTIONALLY_DISABLED**: Blocked until authorized deck provided. | Blocked under governance directive |
| **UIJ-09** | `J-09` | IELTS Full-Length Practice Exam | Bundled academic IELTS paper seeded and published. | **UNVERIFIED / HELD**: Paper kept unpublished pending listening audio synthesis and rights review. | Journey J-09 gate: unpublished status enforced |
| **UIJ-10** | `J-10` | External Cloud Integrations | Third-party OAuth, Firebase, and SMTP integrations. | **INTENTIONALLY_DISABLED**: Local parity utilizes local-only authenticators and Mailpit. | `python scripts/security/verify_independent_config.py` |

---

## 11. Dimension 9: Automated Tests & Quality Gates

### 11.1 Context & Objectives
Ensure that all automated test suites across backend, AI service, Flutter client, and documentation remain green, establishing continuous regression prevention.

### 11.2 Measurable Pass/Fail Criteria

| Check ID | Test Scope | Target Test Suite | Measurable Condition (Pass Criteria) | Failure Condition (Fail Criteria) | Exact Verification Command |
|---|---|---|---|---|---|
| **TST-01** | Provenance Manifest Test | Data Provenance Catalog | All 5 test cases and 43 subtests pass; exit code 0. | Any assertion failure or invalid foreign key reference. | `python -m pytest docs/tests/test_local_data_provenance_manifest.py -q` |
| **TST-02** | Backend Isolated Suite | Full Backend Test Suite | Runner creates isolated UUID test DB; 1679+ tests pass, 3 skipped; exit code 0. | Any test failure, error, or unhandled DB exception. | `cd backend-service && python -m scripts.run_isolated_tests` |
| **TST-03** | Content Agent Validation | Pure Validation Unit Tests | All 32 validation test cases pass; exit code 0. | Schema, CEFR, POS, or URL regex validation regression. | `pytest backend-service/tests/test_content_agent_validation.py -q` |
| **TST-04** | Content Agent Contract | Pydantic Schema Contracts | All 11 contract tests pass; exit code 0. | Contract definition or fixture serialization error. | `pytest backend-service/tests/test_content_agent_contract.py -q` |
| **TST-05** | Content Contract Parity | Cross-Service Schema Parity | All 4 contract parity tests pass; exit code 0. | Divergence between backend and AI contract models. | `pytest backend-service/tests/test_content_contract_parity.py -q` |
| **TST-06** | Python Static Linting | Backend & Scripts Codebase | Ruff check passes with 0 lint errors across `app`, `scripts`, `tests`. | Lint violations, syntax errors, or unused imports. | `cd backend-service && ruff check app scripts tests` |
| **TST-07** | Flutter Config & Network Tests | Flutter Client Unit Tests | All 5 environment and Firebase option tests pass; exit code 0. | Environment parsing error or legacy host fallback. | `cd flutter-app && flutter test test/core/network/api_config_environment_test.dart test/core/services/firebase_options_test.dart` |
| **TST-08** | Flutter Static Analysis | Flutter Client Codebase | `flutter analyze` passes with 0 errors. | Dart analysis errors or fatal warnings. | `cd flutter-app && flutter analyze --no-fatal-warnings --no-fatal-infos` |
| **TST-09** | Local Dev Tooling Suite | PowerShell Dev Utilities | All 9 Pester test cases pass; exit code 0. | Script syntax error or broken container management. | `Invoke-Pester scripts/tests/DevLocal.Tests.ps1` |
| **TST-10** | Security & Independence Sentinel | Tree-wide Coupling Guard | Sentinel reports `Independence/secret sentinel passed.` Exit code 0. | Detection of `lexilingo.me` or unapproved cloud secrets. | `python scripts/security/verify_independent_config.py` |

---

## 12. Dimension 10: Rollback & Disaster Recovery

### 12.1 Context & Objectives
Define explicit mechanisms and verifiable criteria for completely reverting failed migrations, aborted content applications, corrupted demo seeds, or faulty container deployments.

### 12.2 Measurable Pass/Fail Criteria

| Check ID | Rollback Scenario | Target Mechanism / Handler | Measurable Condition (Pass Criteria) | Failure Condition (Fail Criteria) | Verification Method & Command |
|---|---|---|---|---|---|
| **ROL-01** | Content Agent Apply Transaction Abort | `ContentAgentApplyService.apply` ([`backend-service/app/services/content_agent_apply.py`](../../backend-service/app/services/content_agent_apply.py)) | In the event of an uncaught exception, transaction executes `await session.rollback()`; zero courses, units, lessons, or junction rows are committed. | Partial course tree remains committed (e.g. course created without units, or lessons missing exercises). | Unit test with mocked failure: `pytest backend-service/tests/test_content_agent_apply.py -k rollback -q` (TBD: test name) |
| **ROL-02** | Database Schema Migration Rollback | Alembic Migration Engine | Executing `alembic downgrade -1` cleanly rolls back latest migration, drops tables/columns, and updates `alembic_version`. | Migration rollback throws SQL syntax error, fails on table dependencies, or leaves orphaned tables. | `cd backend-service && alembic downgrade -1` followed by `alembic upgrade head` |
| **ROL-03** | Course Content Importer Abort | [`backend-service/scripts/import_course_content.py`](../../backend-service/scripts/import_course_content.py) | Uncaught SQL or parsing error cancels transaction block; database state remains identical to pre-import state. | Script commits partial table rows before failing on subsequent table. | Verified by dry-run rollback test in `import_course_content.py` |
| **ROL-04** | Synthetic Persona Complete Reset | `seed_demo_data.py` & `seed_analytics.py` Wipe Blocks | Running reset logic completely purges `demo_%@lexilingo.dev`, `@lexilingo.test`, and `admin*@lexilingo.dev` accounts and cascades. | Scoped wipe leaves lingering activity rows, wallet balances, or streak records. | Pre/post query: `SELECT count(*) FROM users WHERE email LIKE 'demo_%@lexilingo.dev';` (Becomes 0 before reseed) |
| **ROL-05** | Service Container Rollback Tagging | Docker Container Deployment | Before rebuilding or updating any container, existing running image is tagged: `docker tag lexilingo-ai-service:latest lexilingo-ai-service:rollback`. | Rebuilding container overwrites `:latest` without rollback image, leaving no recovery path on startup crash. | Shell command: `docker tag lexilingo-ai-service:latest lexilingo-ai-service:rollback` |

---

## 13. Dimension 11: Explicit Blocked Conditions

### 13.1 Context & Objectives
Enumerate all hard architectural, legal, and operational prohibitions that must trigger an immediate fail-closed abort.

### 13.2 Measurable Blocked Conditions Matrix

| Block ID | Prohibited Action / Pattern | Target Path / Artifact | Enforcement Mechanism | Pass Standard (Action Blocked) | Fatal Violation Condition |
|---|---|---|---|---|---|
| **BLK-01** | Live External Web Crawling & RSS Feeds | [`backend-service/scripts/seed_empty_tables_and_crawl.py`](../../backend-service/scripts/seed_empty_tables_and_crawl.py), [`ai-service/scripts/crawl_knowledge.py`](../../ai-service/scripts/crawl_knowledge.py), [`ai-service/scripts/crawl_topic_knowledge.py`](../../ai-service/scripts/crawl_topic_knowledge.py) | Governance policy; network isolation | Script execution disabled; zero outbound HTTP requests to external publishers. | Invoking crawl scripts in local dev; making outbound HTTP requests to BBC, NASA, NYT, Guardian. |
| **BLK-02** | Seeding Personal Author Accounts | [`backend-service/scripts/seed_nhthang.py`](../../backend-service/scripts/seed_nhthang.py), [`backend-service/scripts/seed_proficiency_data.py`](../../backend-service/scripts/seed_proficiency_data.py) | Security sentinel; CI check | Scripts strictly excluded from demo entrypoints; `nhthang312@gmail.com` absent from DB. | Executing personal seed scripts; presence of `nhthang312@gmail.com` in demo database. |
| **BLK-03** | Ingesting Unverified Vocabulary Wordlist | [`scripts/categorized_words_final.json`](../../scripts/categorized_words_final.json) | Provenance status `unverified`; disposition `hold_pending_rights` | File quarantined from standard demo seed until rights manifest is authored and approved. | Loading 6,298 unverified words into `vocabulary_items` in Demo Pack v1. |
| **BLK-04** | Ingesting Unverified Conversational Stories | [`ai-service/data/sample_stories.json`](../../ai-service/data/sample_stories.json) | Provenance status `unverified`; disposition `hold_pending_rights` | File quarantined from MongoDB runtime seed until text and image licensing is confirmed. | Seeding `sample_stories.json` into MongoDB via `seed_stories.py` without provenance manifest. |
| **BLK-05** | Ingesting Unverified Knowledge Graphs | [`ai-service/data/kg/06_tracecag_topic_expansion.json`](../../ai-service/data/kg/06_tracecag_topic_expansion.json), [`07_vocabulary_anki.json`](../../ai-service/data/kg/07_vocabulary_anki.json) | Provenance status `unverified`; disposition `hold_pending_rights` | Runtime Kuzu graph build excludes unverified crawled and Anki graph subsets. | Rebuilding runtime graph with unvetted expansion files. |
| **BLK-06** | Publishing Proprietary IELTS Exam Paper | [`backend-service/scripts/ielts_paper_academic_1.py`](../../backend-service/scripts/ielts_paper_academic_1.py), [`backend-service/scripts/seed_ielts_test.py`](../../backend-service/scripts/seed_ielts_test.py) | `Course.is_published = False`; missing audio gate | Paper seeded strictly as unpublished draft; publishing blocked until audio synthesis and rights review. | Setting `is_published = True` on bundled IELTS paper without audio assets or licensing. |
| **BLK-07** | Calls to Legacy Production Endpoints | Deployable source tree references | [`scripts/security/verify_independent_config.py`](../../scripts/security/verify_independent_config.py) | Zero runtime references to `api.lexilingo.me`, `ai.lexilingo.me`, or `lexilingo-88492`. | Runtime code attempting connection to original author's cloud infrastructure. |
| **BLK-08** | Publishing Courses with Unplayable Lessons | Course Publishing Transition | `CourseCRUD.publish_blockers` ([`backend-service/app/models/course.py`](../../backend-service/app/models/course.py)) | Transitioning course to `is_published = True` rejected with 400/409 if any lesson has empty `content.exercises`. | Course published with empty lessons, causing 409 Conflict errors for learners on mobile/web. |
| **BLK-09** | Ingesting Unpinned Content ETL Datasets | AI Service Content ETL Pipeline | `ai-service/api/services/content_etl/contracts.py` | Production ETL refuses to run unless dataset reference and SHA-256 checksum are pinned in environment. | Running production ETL against moving refs (e.g. `main`, `HEAD`, `latest`) or unpinned datasets. |

---

## 14. Verification Command Runbook & Evidence Registry

The table below catalogs every command cited in this specification, confirming its executable syntax and repository evidence base:

```powershell
# ==============================================================================
# LEXILINGO / AI-ENGLISH ACCEPTANCE GATE VERIFICATION RUNBOOK
# ==============================================================================

# 1. Security & Independence Sentinel Gate
python scripts/security/verify_independent_config.py

# 2. Local Data Provenance Manifest Structural Gate
python -m pytest docs/tests/test_local_data_provenance_manifest.py -q

# 3. Content Agent Validation & Contract Unit Gates
python -m pytest backend-service/tests/test_content_agent_validation.py -q
python -m pytest backend-service/tests/test_content_agent_contract.py -q
python -m pytest backend-service/tests/test_content_contract_parity.py -q

# 4. Backend Isolated Database Integration Suite (Full isolated run)
Push-Location backend-service
python -m scripts.run_isolated_tests
ruff check app scripts tests
Pop-Location

# 5. Course Content Playability Audit
python backend-service/scripts/audit_course_content.py

# 6. Minimal Shop Catalog Seeding Idempotency Verification (J-02)
# Run 1: Seeds 54, Updates 0
python backend-service/scripts/seed_shop_items.py
# Run 2: Seeds 0, Updates 54
python backend-service/scripts/seed_shop_items.py

# 7. Sample Courses & Categories Direct Seeding (J-04)
# BLOCKED: do not execute seed_courses_directly.py unless the exact learning
# artifact is approved in the tracked provenance manifest.

# 8. Synthetic Demo Personas Seeding (J-03)
python backend-service/scripts/seed_demo_data.py
python backend-service/scripts/seed_analytics.py

# 9. Flutter Client Configuration & Static Analysis Gates
Push-Location flutter-app
flutter test test/core/network/api_config_environment_test.dart test/core/services/firebase_options_test.dart
flutter analyze --no-fatal-warnings --no-fatal-infos
Pop-Location

# 10. Developer Local Tooling & Orchestration Gate
Invoke-Pester scripts/tests/DevLocal.Tests.ps1

# 11. Git Worktree Modification Isolation Check
git diff --check docs/demo-data/acceptance-matrix-v1.md
```

### 14.1 Registry of TBD Commands
The following operational capabilities are recognized as architectural requirements but currently lack dedicated single-command CLI interfaces in the repository:
* `TBD-01`: CLI dry-run flag for `seed_shop_items.py` (e.g. `python seed_shop_items.py --dry-run`). Currently requires running within isolated runner (`run_isolated_tests.py`).
* `TBD-02`: CLI dry-run flag for `seed_demo_data.py` and `seed_analytics.py`. Currently requires isolated database execution.
* `TBD-03`: End-to-end automated UI journey test runner for Flutter Web (e.g. `flutter drive --target=test_driver/learning_journey.dart`). Currently validated via unit/widget tests and manual web port verification.
* `TBD-04`: Dedicated rollback verification test for `ContentAgentApplyService.apply` (e.g. `pytest backend-service/tests/test_content_agent_apply.py -k test_rollback`).

---

## 15. Sign-Off & Verification Evidence

### 15.1 Path Audit & Existence Confirmation
All paths cited in this document were validated against the local repository filesystem prior to publication. Every cited path exists:
* Contract Schemas: [`contracts/content-agent/source-record-v2.schema.json`](../../contracts/content-agent/source-record-v2.schema.json), [`contracts/content-agent/course-artifact-v2.schema.json`](../../contracts/content-agent/course-artifact-v2.schema.json), [`contracts/content-agent/exercise-types-v1.json`](../../contracts/content-agent/exercise-types-v1.json), [`contracts/content-agent/fixtures/licensed-etl-artifact-v2.json`](../../contracts/content-agent/fixtures/licensed-etl-artifact-v2.json)
* Backend Services & Models: [`backend-service/app/services/content_agent_validation.py`](../../backend-service/app/services/content_agent_validation.py), [`backend-service/app/services/content_agent_apply.py`](../../backend-service/app/services/content_agent_apply.py), [`backend-service/app/services/vocabulary_catalog.py`](../../backend-service/app/services/vocabulary_catalog.py), [`backend-service/app/models/course.py`](../../backend-service/app/models/course.py), [`backend-service/app/models/content_agent.py`](../../backend-service/app/models/content_agent.py), [`backend-service/app/models/vocabulary.py`](../../backend-service/app/models/vocabulary.py)
* Seed Scripts: [`backend-service/scripts/bootstrap_local.py`](../../backend-service/scripts/bootstrap_local.py), [`backend-service/scripts/seed_shop_items.py`](../../backend-service/scripts/seed_shop_items.py), [`backend-service/scripts/seed_courses_directly.py`](../../backend-service/scripts/seed_courses_directly.py), [`backend-service/scripts/seed_demo_data.py`](../../backend-service/scripts/seed_demo_data.py), [`backend-service/scripts/seed_analytics.py`](../../backend-service/scripts/seed_analytics.py), [`backend-service/scripts/audit_course_content.py`](../../backend-service/scripts/audit_course_content.py), [`backend-service/scripts/import_course_content.py`](../../backend-service/scripts/import_course_content.py)
* Test Suites: [`docs/tests/test_local_data_provenance_manifest.py`](../tests/test_local_data_provenance_manifest.py), [`backend-service/tests/test_content_agent_validation.py`](../../backend-service/tests/test_content_agent_validation.py), [`backend-service/tests/test_content_agent_contract.py`](../../backend-service/tests/test_content_agent_contract.py), [`backend-service/tests/test_content_contract_parity.py`](../../backend-service/tests/test_content_contract_parity.py), [`scripts/tests/DevLocal.Tests.ps1`](../../scripts/tests/DevLocal.Tests.ps1)
* Governance Documents: [`docs/INDEPENDENT_DEVELOPMENT_PLAN.md`](../INDEPENDENT_DEVELOPMENT_PLAN.md), [`docs/LOCAL_PARITY_JOURNEY_LEDGER.md`](../LOCAL_PARITY_JOURNEY_LEDGER.md), [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json), [`docs/LOCAL_VALIDATION_REPORT.md`](../LOCAL_VALIDATION_REPORT.md)

### 15.2 Quality Gate & Isolation Status
* **Zero Network Calls:** Completed using local filesystem analysis only.
* **Zero Mutation of Code/Config:** No code, database schemas, configs, or other documentation files were modified.
* **Preservation of Dirty Worktree:** All pre-existing modified files in git status were strictly preserved.
* **Git Diff Check:** Confirmed cleanly passing `git diff --check` with zero whitespace errors or merge conflicts.
