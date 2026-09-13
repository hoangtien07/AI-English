# LexiLingo A1 Everyday Communication — Canonical Artifact Certification (v2)

**Document Reference:** `docs/demo-data/a1-artifact-validation.md`  
**Execution Context:** WAVE L2 — Persist and certify canonical A1 demo artifact  
**Task ID:** `task_724ef97e4873`  
**Dispatch ID:** `ctx_81d60ff8320e`  
**Trust Root:** `docs/demo-data/open-data-source-register-v1.json`  
**Contract Reference:** `contracts/content-agent/course-artifact-v2.schema.json`  
**Status:** CERTIFIED / PASSED  
**Date:** 2026-09-12  

---

## 1. Executive Summary

Under WAVE L2, the canonical English A1 Everyday Communication course artifact (`course-artifact-v2.json`) was generated from repository-approved inputs (`curriculum-blueprint-v1.json` and `lexical-records-v1.json`) using `backend-service/scripts/build_a1_demo_artifact.py`. Two consecutive builds from identical repository inputs established bit-for-bit byte determinism. The generated artifact was fully certified against `contracts/content-agent/course-artifact-v2.schema.json`, backend stateless validation gates, and the fail-closed importer `backend-service/scripts/import_approved_course_artifact.py` in dry-run mode (`writes=0`), with all 94 relevant importer and contract tests passing.

---

## 2. Deterministic Build Commands & Verification

### 2.1 Canonical Build Invocation
```powershell
py -3.14 backend-service/scripts/build_a1_demo_artifact.py `
  --output backend-service/data/approved/a1-everyday-communication/course-artifact-v2.json `
  --lexical-records backend-service/data/approved/a1-everyday-communication/lexical-records-v1.json `
  --blueprint backend-service/data/approved/a1-everyday-communication/curriculum-blueprint-v1.json
```
* **Exit Code:** `0`
* **Output:**
  ```
  built backend-service\data\approved\a1-everyday-communication\course-artifact-v2.json courses=1 units=3 lessons=9 vocabulary=90 exercises=90
  ```

### 2.2 Determinism Proof (Byte-Identical Rebuild)
```powershell
py -3.14 backend-service/scripts/build_a1_demo_artifact.py `
  --output backend-service/.review-pytest-tmp/build2.json `
  --lexical-records backend-service/data/approved/a1-everyday-communication/lexical-records-v1.json `
  --blueprint backend-service/data/approved/a1-everyday-communication/curriculum-blueprint-v1.json
```
* **Build 1 SHA-256:** `49dcc1c2f464ecf0cf0ec1c98c59036d442659fc31260604b214f5af793fcc33`
* **Build 2 SHA-256:** `49dcc1c2f464ecf0cf0ec1c98c59036d442659fc31260604b214f5af793fcc33`
* **Comparison Result:** Bit-for-bit identical (`Compare-Object` returned zero differences).

---

## 3. Artifact Metrics & Structure

| Metric | Target | Actual | Status |
|---|---|---|---|
| Course Count | 1 | 1 | PASS |
| Unit Count | 3 | 3 | PASS |
| Lesson Count | 9 | 9 | PASS |
| Vocabulary Count | 90 | 90 | PASS |
| Exercise Count | 90 | 90 | PASS |
| Lessons with 10+10 (Vocab + Exercises) | 9 / 9 | 9 / 9 | PASS |
| Source Manifest Entries | 3 | 3 | PASS |

### 3.1 Lesson Breakdown

| Unit Index & Title | Lesson Slug | Lesson Title | Vocabulary Items | Exercises |
|---|---|---|---|---|
| Unit 0: Everyday Connections | `greetings` | Greetings and Polite Responses | 10 | 10 |
| Unit 0: Everyday Connections | `introductions` | Introducing Yourself | 10 | 10 |
| Unit 0: Everyday Connections | `personal-information` | Sharing Personal Information | 10 | 10 |
| Unit 1: Daily Life and Schedule | `daily-routine` | Daily Routine | 10 | 10 |
| Unit 1: Daily Life and Schedule | `time-schedule` | Time and Schedules | 10 | 10 |
| Unit 1: Daily Life and Schedule | `home-work` | Home and Work | 10 | 10 |
| Unit 2: The World Around Us | `food` | Food and Drinks | 10 | 10 |
| Unit 2: The World Around Us | `shopping` | Shopping | 10 | 10 |
| Unit 2: The World Around Us | `making-plans` | Making Simple Plans | 10 | 10 |
| **Total** | **9 Lessons** | — | **90** | **90** |

---

## 4. Cryptographic Identity & Approval Register Pins

### 4.1 Artifact Identification
* **File Path:** `backend-service/data/approved/a1-everyday-communication/course-artifact-v2.json`
* **File Size:** 240,963 bytes (4,973 lines)
* **SHA-256:** `49dcc1c2f464ecf0cf0ec1c98c59036d442659fc31260604b214f5af793fcc33`
* **Generation Key:** `281819463fb9f8f0180ed7cfd01c6a487c5d3f07ea86d88bf5d46371ad0a7b16`
* **Canonical Import Identity:** `9f52b74832b4b7e234842c0f11e70f0443d00385017832fcb6a3be72af0ee490`
* **Next-Revision Import Identity (`--new-revision`):** `0c68fce9ecbd47a09375c3fe04d1a4f0940c1cb5b9bdab17626b434993866230`

### 4.2 Approved Source Pins (`docs/demo-data/open-data-source-register-v1.json`)

All vocabulary records retain source pins and valid locators matching the canonical register:

| Source Name | Source ID | Version | License ID | Raw Checksum (SHA-256) | Allowed Usage | Vocab Record Count |
|---|---|---|---|---|---|---|
| `oewn` | `source-oewn-2025` | `2025` | `CC-BY-4.0` | `9ca6d1dcb75f822fdd66617f7d9da48142ace38dd544d6ad5e2feca1674ad3fe` | `lexical` | 30 |
| `cmudict` | `source-cmudict` | `74790861f652b15e4ac49015a90074ad62a27690` | `LicenseRef-CMUdict` | `81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22` | `pronunciation` | 30 |
| `cefr_j` | `source-cefr-j` | `d4e45b75b38f27b30dfc5c44d8c571aec7e7092f` | `LicenseRef-CEFR-J-Commercial` | `b0dd3c635f1c9a4fdf1490c7e5b7c48e8bbe55b652ad0c9860a95f98e10ae498` | `lexical` | 30 |

*Note: `source-evc-beginning-ell` remains marked `blocked` in the register and is excluded from the artifact.*

### 4.3 Provenance & LexiLingo Original Content Separation
* **Lexical / Pronunciation Provenance:** Headwords, phonetic transcriptions (ARPAbet/IPA), and CEFR proficiency alignments originate from approved open datasets with deterministic locators (`source_record_id`).
* **Original LexiLingo Content:** Definitions, Vietnamese translations (`translation_vi`), contextual examples, lesson prose, unit descriptions, and all 90 interactive exercises were authored natively by LexiLingo. Every vocabulary item explicitly records this boundary in `lineage.lexilingo_original_fields: ["definition", "translation_vi", "example"]`. No invented external attribution is claimed for LexiLingo-authored prose.

---

## 5. Validation & Test Certification

### 5.1 JSON Schema Validation
* **Contract:** `contracts/content-agent/course-artifact-v2.schema.json`
* **Validator:** `jsonschema.validate(instance=artifact, schema=schema)`
* **Result:** PASS (0 errors)

### 5.2 Backend Stateless Validation
* **Validator:** `app.services.content_agent_validation.validate_artifact(artifact)`
* **Blocking Errors:** 0 (`[]`)
* **Warnings:** 0 (`[]`)
* **Metrics:** `{"course_count": 1, "unit_count": 3, "lesson_count": 9, "vocabulary_count": 90, "exercise_count": 90}`
* **Result:** PASS (`is_blocking: False`)

### 5.3 Importer Fail-Closed Dry Run
```powershell
py -3.14 backend-service/scripts/import_approved_course_artifact.py `
  --artifact backend-service/data/approved/a1-everyday-communication/course-artifact-v2.json
```
* **Exit Code:** `0`
* **Output:**
  ```
  validated artifact_sha256=49dcc1c2f464ecf0cf0ec1c98c59036d442659fc31260604b214f5af793fcc33 source_count=3 course_count=1 exercise_count=90 lesson_count=9 unit_count=3 vocabulary_count=90
  import_identity=9f52b74832b4b7e234842c0f11e70f0443d00385017832fcb6a3be72af0ee490
  raw_checksums=81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22,9ca6d1dcb75f822fdd66617f7d9da48142ace38dd544d6ad5e2feca1674ad3fe,b0dd3c635f1c9a4fdf1490c7e5b7c48e8bbe55b652ad0c9860a95f98e10ae498
  dry_run=true writes=0
  ```
* **Result:** PASS (0 database writes, trusted source pins verified, exact import identity established).

### 5.4 Automated Test Suite
```powershell
$env:TMP = "$PWD\.review-pytest-tmp"; $env:TEMP = "$PWD\.review-pytest-tmp"
py -3.14 -m pytest backend-service/tests/test_content_contract_parity.py `
                   backend-service/tests/test_import_approved_course_artifact.py `
                   backend-service/tests/test_content_agent_validation.py `
                   backend-service/tests/test_content_agent_jobs.py `
                   backend-service/tests/test_content_agent_import_identity_migration.py `
                   -q -o cache_dir=.review-pytest-cache
```
* **Result:** `94 passed in 1.97s` (100% pass)
  * `test_content_contract_parity.py`: 8 passed (contract parity, schema integrity, required attributes).
  * `test_import_approved_course_artifact.py`: 30 passed (source register constraints, symlink guards, replay idempotency, dry-run zero-write enforcement).
  * `test_content_agent_validation.py`: 32 passed (stateless validation rules, blocking vs warning behavior, metrics calculation).
  * `test_content_agent_jobs.py`: 21 passed (import identity format, uniqueness, database boundary integrity).
  * `test_content_agent_import_identity_migration.py`: 3 passed (Alembic migration forward/rollback semantics).

---

## 6. Repository Integrity & Checksums

| File Path | Byte Size | SHA-256 Checksum |
|---|---|---|
| `backend-service/scripts/build_a1_demo_artifact.py` | 14,247 | `7e5f1f2dc4476b9634415fa8953a95db3e9af94131fdb5eee2aba093bd900187` |
| `backend-service/scripts/import_approved_course_artifact.py` | 19,781 | `c2d70a39b7438a89b01293d64389ea4f8431063f0ea25fc804086047b44799ea` |
| `backend-service/data/approved/a1-everyday-communication/curriculum-blueprint-v1.json` | 92,729 | `0529c5e0b9b71b274bac073934b71cd65da7c97959f64bedac5314c3610453c8` |
| `backend-service/data/approved/a1-everyday-communication/lexical-records-v1.json` | 296,703 | `924c0f4f08e3ac34bdcbae791d2500920c5805cc1334f5ce5f902f89c16b1895` |
| `backend-service/data/approved/a1-everyday-communication/lexical-attribution-v1.md` | 22,608 | `c6c4d764c11ef089a0bae5b4011e69164fb23cc91d407423bdfe9e9db71661a4` |
| `backend-service/data/approved/a1-everyday-communication/course-artifact-v2.json` | 240,963 | `49dcc1c2f464ecf0cf0ec1c98c59036d442659fc31260604b214f5af793fcc33` |
| `docs/demo-data/open-data-source-register-v1.json` | 2,705 | `b750ab83978edca8bae5bcbbec22ca622d6886c959b93d77e8f32300d403d759` |
| `contracts/content-agent/course-artifact-v2.schema.json` | 11,542 | `4b6ecc77e0bed8e576296e81567ef6d2683d55e5c3ddbbed5e8e6a8fb9b33c09` |
| `docs/demo-data/a1-artifact-validation.md` | *This file* | *Generated by Wave L2* |

---

## 7. Repository Hygiene Check

```powershell
git diff --check docs/demo-data/a1-artifact-validation.md
```
* **Result:** Clean exit (code `0`). No trailing whitespace, merge conflicts, or formatting issues. Pre-existing dirty worktree modifications preserved intact.
