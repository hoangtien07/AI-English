# LexiLingo Source & Artifact Inventory Specification (v1)

**Document Reference:** `docs/demo-data/source-inventory-v1.md`
**Execution Context:** WAVE A1 — Source and Artifact Inventory
**Target Repository:** `C:\Users\hoang\orca\workspaces\lexilingo-clean-v1\run-local`
**Author / Engine:** Antigravity 3.8 Flash (Dispatched Worker `task_e64812cd3606`)
**Status:** Canonical Reference & Baseline Inventory (Read-Only Discovery)
**Date:** 2026-09-10

---

## 1. Executive Summary & Inventory Objectives

### 1.1 Purpose & Scope
This document provides the definitive repository-local inventory of all existing learning content, seed scripts, datasets, fixtures, schemas, and pipelines across the LexiLingo / AI-English codebase. It establishes the baseline data classification required to assemble an authorized, fully functional, and legally unencumbered **Demo Pack v1** for local development and demonstration.

This audit was conducted strictly under repository-local discovery rules without performing any network requests, external crawling, data imports, database mutations, or secret reads. Existing uncommitted working-tree modifications across the repository were strictly preserved.

### 1.2 Core Governance Policies
In strict compliance with [`AGENTS.md`](../../AGENTS.md), [`docs/INDEPENDENT_DEVELOPMENT_PLAN.md`](../INDEPENDENT_DEVELOPMENT_PLAN.md), [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json), and [`docs/LOCAL_PARITY_JOURNEY_LEDGER.md`](../LOCAL_PARITY_JOURNEY_LEDGER.md), the following governance rules are enforced:

1. **No Inference of Content Rights from Software License:** The software MIT license in [`LICENSE`](../../LICENSE) covers code and software documentation only; it does not grant copyright or redistribution rights for bundled vocabulary datasets, language corpora, exam papers, or story texts.
2. **Public Availability ≠ Content License:** The fact that an RSS feed, website endpoint, or third-party file is publicly accessible does not grant legal authorization to scrape, duplicate, or redistribute its content.
3. **Prohibition of Personal / Production Data:** Any dataset, seed script, or test profile containing real user accounts, developer credentials, or production activity records (specifically including personal emails such as `nhthang312@gmail.com`) is strictly prohibited from Demo Pack v1.
4. **Fail-Closed External Collection:** Automated crawlers and external data acquisition scripts are held in a disabled status pending explicit written licensing decisions.
5. **Reproducible Provenance Records:** Every artifact considered for demo inclusion must maintain an auditable trail including exact repository path, byte size, format, record count, schema structure, and idempotency characteristics.

---

## 2. Master Source-to-Artifact Inventory Table

The table below catalogs every discovered content artifact and seed entrypoint in the repository, mapping each to its origin source, exact physical metrics, schema shape, runtime entrypoint, provenance classification, and v1 demo disposition.

| Source Origin | Artifact Path(s) | Format | Byte Size | Record Count & Schema Shape | Existing Seed / Import Entrypoint | Provenance Status | v1 Disposition |
|---|---|---|---|---|---|---|---|
| **Repository Software License** (`source-repository-mit`) | [`LICENSE`](../../LICENSE) | Plain text | 1,090 bytes | 1 text file (21 lines); standard MIT legal text | None (Legal metadata) | `repository_license_only` | `not_content_license` (Software license only) |
| **Built-in Shop Catalog** (`source-repository-authored-seed`) | [`backend-service/app/core/shop_catalog.py`](../../backend-service/app/core/shop_catalog.py) | Python module | 6,581 bytes | 54 shop items (18 consumable/game powerup items, 36 avatar items); Schema: `Dict[name, description, item_type, price_gems, icon_url, effects, is_available]` | [`backend-service/scripts/seed_shop_items.py`](../../backend-service/scripts/seed_shop_items.py); [`backend-service/app/services/admin_seed_service.py`](../../backend-service/app/services/admin_seed_service.py) | `repository_license_only` | `minimal_local_seed_candidate` |
| **Built-in Sample Courses & Gamification** (`source-unattributed-repository-content`) | [`backend-service/app/core/sample_data_catalog.py`](../../backend-service/app/core/sample_data_catalog.py) | Python module | 28,912 bytes | 4 achievements, 2 course categories, 2 A1 courses (2 units, 4 lessons, 40 interactive exercises); Schema: Hierarchical Courses -> Units -> Lessons -> Exercises | [`backend-service/scripts/seed_courses_directly.py`](../../backend-service/scripts/seed_courses_directly.py); [`backend-service/app/services/admin_seed_service.py`](../../backend-service/app/services/admin_seed_service.py) | `unverified` (uncataloged in manifest) | `hold_pending_rights` (fail-closed quarantine) |
| **Local Database Bootstrap** (`source-repository-authored-seed`) | [`backend-service/scripts/bootstrap_local.py`](../../backend-service/scripts/bootstrap_local.py) | Python script | 2,018 bytes | 65 lines; Alembic migration execution wrapper (`alembic upgrade head`) | [`backend-service/scripts/bootstrap_local.py`](../../backend-service/scripts/bootstrap_local.py) | `repository_license_only` | `minimal_local_seed_candidate` (Prerequisite bootstrap) |
| **Synthetic Demo Personas** (`source-synthetic-demo-personas`) | [`backend-service/scripts/seed_demo_data.py`](../../backend-service/scripts/seed_demo_data.py) | Python script | 24,971 bytes | 45 synthetic learner accounts (`demo_%@lexilingo.dev`), 90 days activity history, daily activities, streaks, enrollments, completions | [`backend-service/scripts/seed_demo_data.py`](../../backend-service/scripts/seed_demo_data.py) | `synthetic` | `minimal_local_seed_candidate` (Isolated demo database only) |
| **Synthetic Analytics Personas** (`source-synthetic-demo-personas`) | [`backend-service/scripts/seed_analytics.py`](../../backend-service/scripts/seed_analytics.py) | Python script | 38,921 bytes | Deterministic synthetic accounts (`@lexilingo.test`, `admin*@lexilingo.dev`, seed=42); wallets, XP transactions, game sessions, leaderboard entries | [`backend-service/scripts/seed_analytics.py`](../../backend-service/scripts/seed_analytics.py) | `synthetic` | `minimal_local_seed_candidate` (Isolated demo database only) |
| **Licensed ETL Contract Fixture** (`source-test-fixture-declarations`) | [`contracts/content-agent/fixtures/licensed-etl-artifact-v2.json`](../../contracts/content-agent/fixtures/licensed-etl-artifact-v2.json) | JSON object | 14,687 bytes | 1 synthetic course ("English A1 Licensed Foundations", 1 unit, 1 lesson, 3 exercises); Schema: Contract v2 with license manifests and synthetic word tokens | Unit tests in `ai-service/tests/test_licensed_content_etl.py` | `fixture_only` | `test_only` |
| **Content ETL Test Fixtures (Mini Corpora)** (`source-test-fixture-declarations`) | [`ai-service/tests/content_etl/fixtures/*`](../../ai-service/tests/content_etl/fixtures) (10 files) | CSV, TSV, XML, Dict, JSON, TXT | 4,755 bytes total (individual files 97B–1,442B) | 10 test fixtures: CEFR-J (6 lines), CMUdict (10 lines), Common Voice (3 lines + metadata JSON), LibriSpeech (3 lines), OEWN (30 lines + release XML), Tatoeba (6 lines across 2 files), Wikidata (3 entities) | Used exclusively in `ai-service/tests/content_etl/` test suites | `fixture_only` | `test_only` |
| **AI Topic Paraphrases Eval Fixture** (`source-test-fixture-declarations`) | [`ai-service/data/eval/topic_paraphrases.json`](../../ai-service/data/eval/topic_paraphrases.json) | JSON array | 17,154 bytes | 60 topic evaluation items; Schema: `List[Dict[topic_id, title, level, queries]]` | [`ai-service/scripts/eval_kg_retrieval.py`](../../ai-service/scripts/eval_kg_retrieval.py); [`ai-service/scripts/eval_answer_quality.py`](../../ai-service/scripts/eval_answer_quality.py) | `fixture_only` | `test_only` |
| **Categorized Vocabulary Wordlist** (`source-unattributed-repository-content`) | [`scripts/categorized_words_final.json`](../../scripts/categorized_words_final.json) | JSON array | 3,637,796 bytes | 6,298 vocabulary entries; Schema: `List[Dict[word, definition, example, phonetic, audios, images, index, tags, translation]]` | [`backend-service/scripts/update_db_tags.py`](../../backend-service/scripts/update_db_tags.py); legacy [`backend-service/scripts/import_json_to_db.py`](../../backend-service/scripts/import_json_to_db.py) | `unverified` | `hold_pending_rights` |
| **Role-Play Conversation Story Blueprints** (`source-unattributed-repository-content`) | [`ai-service/data/sample_stories.json`](../../ai-service/data/sample_stories.json) | JSON object | 461,477 bytes | 68 role-play scenario blueprints (A1–C1); Schema: `Dict[stories: List[Dict[story_id, title, difficulty_level, category, context_description, role_persona, suggested_prompts, grammar_points, cover_image_url...]]]` | [`ai-service/scripts/seed_stories.py`](../../ai-service/scripts/seed_stories.py) | `unverified` | `hold_pending_rights` |
| **Curated Knowledge Graph (Core)** (`source-unattributed-repository-content`) | [`ai-service/data/kg/*.json`](../../ai-service/data/kg) (12 files) | JSON objects | 6,409,864 bytes total (files 7.5KB to 3.38MB) | 15,158 concepts, 14,838 edges across 12 files (grammar gaps, errors, writing, phonology, tracecag topic expansion, anki vocab, cefr sentences, collocations, idioms, seed graph) | [`ai-service/scripts/rebuild_runtime_kg.py`](../../ai-service/scripts/rebuild_runtime_kg.py); `KnowledgeGraphServiceV3` | `unverified` | `hold_pending_rights` |
| **Extended & Enriched Topic Graphs** (`source-unattributed-repository-content`) | [`ai-service/data/knowledge_extended.json`](../../ai-service/data/knowledge_extended.json); [`ai-service/data/topic_graphs.json`](../../ai-service/data/topic_graphs.json); [`ai-service/data/topic_graphs.enriched.json`](../../ai-service/data/topic_graphs.enriched.json) | JSON objects | 67,457 bytes total (19.3KB, 2.7KB, 45.4KB) | 184 concepts, 178 edges total across 3 files; crawled/LLM-enriched concepts with external URL references | [`ai-service/scripts/import_knowledge.py`](../../ai-service/scripts/import_knowledge.py); [`ai-service/scripts/crawl_topic_knowledge.py`](../../ai-service/scripts/crawl_topic_knowledge.py) | `unverified` | `hold_pending_rights` |
| **Modern Slang Editorial Notes** (`source-unattributed-repository-content`) | [`ai-service/data/external_docs/modern_slang.md`](../../ai-service/data/external_docs/modern_slang.md) | Markdown text | 1,209 bytes | 24 lines of informal editorial slang glossary (e.g., rizz, no cap, bet); no attribution or license | None (Static reference document) | `unverified` | `hold_pending_rights` |
| **IELTS Academic Practice Paper 1** (`source-unattributed-repository-content`) | [`backend-service/scripts/ielts_paper_academic_1.py`](../../backend-service/scripts/ielts_paper_academic_1.py) | Python data module | 58,195 bytes | 1,011 lines; Full-length IELTS test: Listening (4 parts, 40 questions), Reading (3 passages, 40 questions), Writing (2 tasks), Speaking (3 parts); total 80 objective + 5 productive tasks | [`backend-service/scripts/seed_ielts_test.py`](../../backend-service/scripts/seed_ielts_test.py) | `unverified` | `hold_pending_rights` |
| **Grammar MCQ Question Bank** (`source-unattributed-repository-content`) | [`backend-service/scripts/seed_questions.py`](../../backend-service/scripts/seed_questions.py) | Python seed script | 51,898 bytes | 1,150 lines; 98 MCQ questions across 27 grammar categories (A1–C2); Schema: `Dict[topic, List[Dict[prompt, options, answer, explanation]]]` | [`backend-service/scripts/seed_questions.py`](../../backend-service/scripts/seed_questions.py) | `unverified` | `hold_pending_rights` |
| **Personal Developer Account Seed** (`source-developer-personal-data`) | [`backend-service/scripts/seed_nhthang.py`](../../backend-service/scripts/seed_nhthang.py) | Python script | 10,319 bytes | 234 lines; Personal account configuration for `nhthang312@gmail.com`: admin role injection, 45 days fake daily activities, course progress | [`backend-service/scripts/seed_nhthang.py`](../../backend-service/scripts/seed_nhthang.py) | `blocked` | `prohibited` (Personal user data / original author account) |
| **Personal Developer Proficiency Seed** (`source-developer-personal-data`) | [`backend-service/scripts/seed_proficiency_data.py`](../../backend-service/scripts/seed_proficiency_data.py) | Python script | 19,926 bytes | 491 lines; Personal proficiency data for `nhthang312@gmail.com`: 500+ exercise attempts, user skill scores, level history (A1->B1) | [`backend-service/scripts/seed_proficiency_data.py`](../../backend-service/scripts/seed_proficiency_data.py) | `blocked` | `prohibited` (Personal user data / original author account) |
| **External RSS Crawl Pipeline** (`source-external-rss-feeds`) | [`backend-service/scripts/seed_empty_tables_and_crawl.py`](../../backend-service/scripts/seed_empty_tables_and_crawl.py) | Python crawl script | 35,773 bytes | 932 lines; Scrapes live RSS feeds from BBC, NASA, NYT, and The Guardian; generates course/lesson rows from uncurated web content | [`backend-service/scripts/seed_empty_tables_and_crawl.py`](../../backend-service/scripts/seed_empty_tables_and_crawl.py) | `blocked` | `prohibited` / `disabled_pending_rights` |
| **External Anki Package Importer** (`source-external-anki-package`) | [`backend-service/scripts/seed_vocab_from_anki.py`](../../backend-service/scripts/seed_vocab_from_anki.py) | Python import script | 12,948 bytes | 358 lines; Parser for unverified operator-supplied SQLite `.apkg` files; maps frequency ranks to CEFR levels | [`backend-service/scripts/seed_vocab_from_anki.py`](../../backend-service/scripts/seed_vocab_from_anki.py) | `blocked` | `disabled_pending_rights` (Deck unverified / prohibited until approved) |
| **Dynamic Web Crawling Scripts** (`source-external-crawl-agents`) | [`ai-service/scripts/crawl_knowledge.py`](../../ai-service/scripts/crawl_knowledge.py); [`ai-service/scripts/crawl_topic_knowledge.py`](../../ai-service/scripts/crawl_topic_knowledge.py) | Python crawl scripts | 49,311 bytes total (6.5KB, 42.8KB) | 153 and 1,101 lines; Web scraping pipelines using `crawl4ai` (Playwright) and Gemini API to scrape external URLs and append to KG | Dynamic execution via CLI | `blocked` | `prohibited` / `disabled_pending_rights` |

---

## 3. Artifacts Explicitly Prohibited from Demo Pack v1

In accordance with [`docs/INDEPENDENT_DEVELOPMENT_PLAN.md`](../INDEPENDENT_DEVELOPMENT_PLAN.md) (Sections 3.1 and 3.2) and [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json), the following artifacts and entrypoints are **strictly prohibited** from inclusion or execution in Demo Pack v1:

```
+---------------------------------------------------------------------------------------------------------+
|                                    DEMO PACK v1 PROHIBITION MATRIX                                     |
+---------------------------------------------------------+---------------------+-------------------------+
| Repository Artifact Path                                | Prohibited Category | Primary Policy Reason   |
+---------------------------------------------------------+---------------------+-------------------------+
| backend-service/scripts/seed_nhthang.py                 | Personal User Data  | Hardcoded personal email|
| backend-service/scripts/seed_proficiency_data.py        | Personal User Data  | Hardcoded personal email|
| backend-service/scripts/seed_empty_tables_and_crawl.py  | Live Web Scraper    | Unlicensed RSS scraping |
| ai-service/scripts/crawl_knowledge.py                   | Live Web Scraper    | Unlicensed web crawl    |
| ai-service/scripts/crawl_topic_knowledge.py             | Live Web Scraper    | Unlicensed web crawl    |
| backend-service/scripts/seed_vocab_from_anki.py         | Unverified External | Unlicensed Anki deck    |
| scripts/categorized_words_final.json                    | Unverified Content  | Missing attribution/CDN |
| backend-service/scripts/ielts_paper_academic_1.py       | Unverified Content  | Unattributed IELTS exam |
| backend-service/scripts/seed_ielts_test.py              | Unverified Content  | Unverified assessment   |
| ai-service/data/kg/06_tracecag_topic_expansion.json     | Unverified Content  | Crawled graph expansion |
| ai-service/data/kg/07_vocabulary_anki.json             | Unverified Content  | Unattributed Anki vocab |
+---------------------------------------------------------+---------------------+-------------------------+
```

### 3.1 Prohibited Category 1: Personal Developer Accounts & Production User Data
* **Repository Paths:**
  - [`backend-service/scripts/seed_nhthang.py`](../../backend-service/scripts/seed_nhthang.py)
  - [`backend-service/scripts/seed_proficiency_data.py`](../../backend-service/scripts/seed_proficiency_data.py)
* **Specific Prohibited Content:**
  - Hardcodes the personal Gmail address `nhthang312@gmail.com` (lines 49 in `seed_proficiency_data.py`, lines 5-6 in `seed_nhthang.py`).
  - Automatically elevates this specific personal account to `admin` role and seeds personalized course progress, lesson completions, 45 days of fake daily activities, and 500+ exercise attempts.
* **Violation Rationale:**
  - Violates [`docs/INDEPENDENT_DEVELOPMENT_PLAN.md`](../INDEPENDENT_DEVELOPMENT_PLAN.md) Section 3.1 ("Never use credentials whose ownership is unknown... Do not copy accounts, personal data, progress, chats, emails, tokens, or private media") and Section 7.2 ("The owner approved one exact super-admin email... Keep privileges exact-address only").
  - Violates [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json) (`policy.original_user_or_production_data: prohibited`).

### 3.2 Prohibited Category 2: Live Network Crawlers & Unlicensed External Feeds
* **Repository Paths:**
  - [`backend-service/scripts/seed_empty_tables_and_crawl.py`](../../backend-service/scripts/seed_empty_tables_and_crawl.py)
  - [`ai-service/scripts/crawl_knowledge.py`](../../ai-service/scripts/crawl_knowledge.py)
  - [`ai-service/scripts/crawl_topic_knowledge.py`](../../ai-service/scripts/crawl_topic_knowledge.py)
* **Specific Prohibited Content:**
  - Live HTTP requests and feed parsing targeting external commercial news publishers: BBC News, NASA, The New York Times, and The Guardian RSS feeds.
  - Automated web scraping via `crawl4ai` (Playwright headless browser) and dynamic Gemini extraction to append arbitrary web content to the knowledge base.
* **Violation Rationale:**
  - Violates [`docs/INDEPENDENT_DEVELOPMENT_PLAN.md`](../INDEPENDENT_DEVELOPMENT_PLAN.md) Section 3.2 ("External acquisition blocked pending written rights decision... Check the site's terms, robots policy... Stop and request owner approval when rights are unclear").
  - Disregards copyright boundaries of third-party publishers and introduces non-deterministic, unvetted runtime dependencies.

### 3.3 Prohibited Category 3: Unvetted Third-Party Packages
* **Repository Path:**
  - [`backend-service/scripts/seed_vocab_from_anki.py`](../../backend-service/scripts/seed_vocab_from_anki.py)
* **Specific Prohibited Content:**
  - Reads external `.apkg` files (e.g. `5000_English_Word_Anki.apkg`) and populates the `vocabulary_items` table without verifying the deck's underlying author, copyright, or commercial reuse license.
* **Violation Rationale:**
  - Reconciled with [`docs/LOCAL_PARITY_JOURNEY_LEDGER.md`](../LOCAL_PARITY_JOURNEY_LEDGER.md) journey `J-08` (`INTENTIONALLY_DISABLED`: "Owner supplies a specific authorized deck and a provenance record; validate the copied fields and attribution before import").

### 3.4 Prohibited Category 4: Unverified Core Learning Datasets (Held Pending Rights)
* **Repository Paths:**
  - [`scripts/categorized_words_final.json`](../../scripts/categorized_words_final.json)
  - [`backend-service/scripts/ielts_paper_academic_1.py`](../../backend-service/scripts/ielts_paper_academic_1.py) & [`backend-service/scripts/seed_ielts_test.py`](../../backend-service/scripts/seed_ielts_test.py)
  - [`ai-service/data/kg/06_tracecag_topic_expansion.json`](../../ai-service/data/kg/06_tracecag_topic_expansion.json) (3.38 MB, 4,040 concepts, 14,640 edges)
  - [`ai-service/data/kg/07_vocabulary_anki.json`](../../ai-service/data/kg/07_vocabulary_anki.json) (1.19 MB, 6,747 concepts)
* **Specific Prohibited Content:**
  - `categorized_words_final.json` contains 6,298 vocabulary items with audio and image links referencing third-party CDNs without accompanying attribution or licensing files.
  - `ielts_paper_academic_1.py` contains full proprietary IELTS examination passages and question structures. Listening audio recordings are missing, and no Cambridge/IELTS licensing agreement is recorded.
  - Knowledge graph expansion files contain crawled web triples and unverified Anki decks.
* **Violation Rationale:**
  - These files are classified as `unverified` and held under `hold_pending_rights`. They cannot be published or distributed in the standard Demo Pack v1 until an authorized content provenance manifest is provided.

---

## 4. Approved Demo Pack v1 Assembly Plan

To ensure a clean, self-contained, and legally unencumbered evaluation experience that fulfills journeys `J-01`, `J-02`, and `J-03` of [`docs/LOCAL_PARITY_JOURNEY_LEDGER.md`](../LOCAL_PARITY_JOURNEY_LEDGER.md), Demo Pack v1 must be composed strictly of the following three layers:

```mermaid
graph TD
    subgraph Layer 1: Schema Bootstrap
        A[backend-service/scripts/bootstrap_local.py] -->|Alembic upgrade head| DB[(PostgreSQL Database)]
    end

    subgraph Layer 2: Approved Repository Catalogs
        SC[backend-service/app/core/shop_catalog.py] -->|seed_shop_items.py| DB
    end

    subgraph Layer 3: Synthetic Activity Personas
        SDD[backend-service/scripts/seed_demo_data.py] -->|demo_%@lexilingo.dev| DB
        SAD[backend-service/scripts/seed_analytics.py] -->|@lexilingo.test seed=42| DB
    end
```

### 4.1 Layer 1: Deterministic Schema Bootstrap
* **Artifact:** [`backend-service/scripts/bootstrap_local.py`](../../backend-service/scripts/bootstrap_local.py)
* **Action:** Executes `alembic upgrade head` inside PostgreSQL.
* **Idempotency:** Safe to run repeatedly; verifies schema integrity and halts if an unmanaged legacy database is detected.
* **Content Ingested:** 0 rows of learning content; establishes schema structure for users, roles, courses, gamification, and proficiency.

### 4.2 Layer 2: Canonical Repository Catalogs (`repository_license_only` / Approved Seed Candidate)
* **Shop Catalog:**
  - **Source Artifact:** [`backend-service/app/core/shop_catalog.py`](../../backend-service/app/core/shop_catalog.py) (6,581 bytes)
  - **Entrypoint:** [`backend-service/scripts/seed_shop_items.py`](../../backend-service/scripts/seed_shop_items.py)
  - **Payload:** 54 items (18 consumable powerups such as Hint Packs, Heart Refills, Streak Freezes, Time Freezes; 36 DiceBear avatar seeds across 3 price tiers).
  - **Idempotency:** Upserts on `ShopItem.name`.
  - **Manifest Status:** Explicitly approved in [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json) as `artifact-minimal-shop-catalog` (`minimal_local_seed_candidate`).

* **Fail-Closed Exclusion of Built-in Courses (`sample_data_catalog.py`):**
  - [`backend-service/app/core/sample_data_catalog.py`](../../backend-service/app/core/sample_data_catalog.py) and [`backend-service/scripts/seed_courses_directly.py`](../../backend-service/scripts/seed_courses_directly.py) are **not explicitly cataloged as approved artifacts** in [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json).
  - The module contains educational course lessons with external Unsplash image links (`images.unsplash.com`) and Vietnamese translations without an approved source rights record.
  - In strict accordance with fail-closed repository governance, `sample_data_catalog.py` is excluded from the approved Demo Pack v1 baseline and quarantined under `hold_pending_rights`.

### 4.3 Layer 3: Synthetic Activity Personas (`synthetic`)
* **Dashboard Demo Data:**
  - **Source Artifact:** [`backend-service/scripts/seed_demo_data.py`](../../backend-service/scripts/seed_demo_data.py) (24,971 bytes)
  - **Payload:** 45 synthetic learner accounts (`demo_%@lexilingo.dev`) with realistic activity across a 90-day window.
  - **Idempotency:** Scoped cleanup deletes only `demo_%@lexilingo.dev` accounts and cascade dependencies before recreating synthetic rows. Real users and reference catalogs are untouched.
* **Deterministic Analytics & Gamification Data:**
  - **Source Artifact:** [`backend-service/scripts/seed_analytics.py`](../../backend-service/scripts/seed_analytics.py) (38,921 bytes)
  - **Payload:** Synthetic users across `@lexilingo.test` and `admin*@lexilingo.dev` namespaces using pseudo-random generation (fixed `random.seed(42)`). Generates wallet balances, XP transactions, game sessions (Hangman, Matching, Word Scramble), and leaderboard positions.
  - **Idempotency:** Scoped cleanup deletes only test email namespaces before reseeding.

---

## 5. Detailed Inventory of Unverified Artifacts (`hold_pending_rights`)

The following repository artifacts contain valuable domain models and educational data, but lack verified license manifests. They must remain quarantined from the default demo seed until the owner or rights holder completes a formal provenance review.

### 5.1 Large Categorized Vocabulary Wordlist
* **Path:** [`scripts/categorized_words_final.json`](../../scripts/categorized_words_final.json)
* **Metrics:** 3,637,796 bytes (3.64 MB), 6,298 records.
* **Schema Shape:**
  ```json
  [
    {
      "word": "abandon",
      "definition": "to leave a place, thing, or person, usually for ever",
      "example": "We had to abandon the car.",
      "phonetic": "/əˈbæn.dən/",
      "audios": {"uk": "https://...", "us": "https://..."},
      "images": ["https://..."],
      "index": 1,
      "tags": ["b2", "oxford_3000", "general"],
      "translation": {"vi": "từ bỏ, bỏ rơi"}
    }
  ]
  ```
* **Risk & Remediation:** The audio and image URLs reference external third-party hosts (`dictionary.cambridge.org`, Wikimedia, Google Cloud storage). A provenance manifest must document the source of definitions and verify image/audio redistribution terms before ingestion.

### 5.2 Conversational Role-Play Stories
* **Path:** [`ai-service/data/sample_stories.json`](../../ai-service/data/sample_stories.json)
* **Metrics:** 461,477 bytes (461.5 KB), 68 records.
* **Schema Shape:**
  ```json
  {
    "stories": [
      {
        "story_id": "story_airport_travel",
        "title": {"en": "Airport Travel Adventure", "vi": "Cuộc phiêu lưu tại sân bay"},
        "difficulty_level": "B1",
        "category": "travel",
        "estimated_minutes": 15,
        "cover_image_url": "https://...",
        "context_description": "You are at Tan Son Nhat Airport...",
        "role_persona": {"ai_role": "Check-in Officer", "user_role": "Passenger"},
        "suggested_prompts": ["Can I check my luggage?", "Where is gate 12?"],
        "grammar_points": ["Present perfect", "Modal verbs"]
      }
    ]
  }
  ```
* **Audit Observations ([`DATA_AUDIT.md`](../../ai-service/data/DATA_AUDIT.md)):** These are conversational role-play blueprints, not complete graded readers. Level distribution is skewed (A1: 4, A2: 12, B1: 28, B2: 17, C1: 7, C2: 0). 5 records contain external image URLs. Ingestion via [`ai-service/scripts/seed_stories.py`](../../ai-service/scripts/seed_stories.py) into MongoDB is blocked until image and text rights are verified.

### 5.3 Knowledge Graph Corpora
* **Paths:** [`ai-service/data/kg/*.json`](../../ai-service/data/kg) (12 files, 6.41 MB total)
* **Detailed Breakdown:**
  1. `01_grammar_gaps.json` (7,569 bytes): 18 concepts, 22 edges.
  2. `02_functional_language.json` (8,313 bytes): 20 concepts, 21 edges.
  3. `03_errors_vietnamese.json` (8,631 bytes): 20 concepts, 23 edges (L1 transfer error labels).
  4. `04_writing_phonology.json` (8,241 bytes): 19 concepts, 23 edges.
  5. `05_vocabulary_advanced.json` (8,412 bytes): 20 concepts, 20 edges.
  6. `06_tracecag_topic_expansion.json` (3,382,945 bytes): 4,040 concepts, 14,640 edges (Crawled and LLM-expanded topic graph; lacks C2 coverage).
  7. `07_vocabulary_anki.json` (1,195,608 bytes): 6,747 concepts, 0 edges (Derived from external Anki export).
  8. `08_cefr_sentences.json` (304,045 bytes): 1,250 concepts, 0 edges.
  9. `09_grammar_usage.json` (1,040,866 bytes): 1,000 concepts, 0 edges.
  10. `10_collocations.json` (191,974 bytes): 1,000 concepts, 0 edges.
  11. `11_idioms.json` (221,512 bytes): 852 concepts, 0 edges.
  12. `seed_graph.json` (31,748 bytes): 92 concepts, 89 edges.
* **Extended Graph Files:**
  - `knowledge_extended.json` (19,325 bytes): 65 concepts, 41 edges.
  - `topic_graphs.json` (2,725 bytes): 8 concepts, 7 edges.
  - `topic_graphs.enriched.json` (45,407 bytes): 111 concepts, 130 edges.
* **Audit Observations ([`DATA_AUDIT.md`](../../ai-service/data/DATA_AUDIT.md)):** Contains duplicate edges and cross-file reference dependencies. Curated files are clean, but `06_tracecag_topic_expansion.json` and `07_vocabulary_anki.json` incorporate third-party data without verified distribution licenses. Rebuilding Kuzu runtime graph via [`ai-service/scripts/rebuild_runtime_kg.py`](../../ai-service/scripts/rebuild_runtime_kg.py) must exclude unverified expansion subsets.

### 5.4 Full-Length IELTS Academic Paper
* **Path:** [`backend-service/scripts/ielts_paper_academic_1.py`](../../backend-service/scripts/ielts_paper_academic_1.py) (58,195 bytes)
* **Metrics:** 1,011 lines; Complete 4-skill paper (Listening: 40 Qs, Reading: 40 Qs, Writing: 2 tasks, Speaking: 3 parts).
* **Entrypoint:** [`backend-service/scripts/seed_ielts_test.py`](../../backend-service/scripts/seed_ielts_test.py) (4,642 bytes).
* **Audit Observations ([`LOCAL_PARITY_JOURNEY_LEDGER.md`](../LOCAL_PARITY_JOURNEY_LEDGER.md) journey `J-09`):** The paper contains complete academic reading and listening transcripts. However, listening audio recordings have not been synthesized or licensed. The paper currently lands **unpublished** in the database. Publishing requires a formal rights assessment of the exam text and synthesis of owned audio assets.

### 5.5 Grammar MCQ Question Bank
* **Path:** [`backend-service/scripts/seed_questions.py`](../../backend-service/scripts/seed_questions.py) (51,898 bytes)
* **Metrics:** 1,150 lines; 98 MCQ questions across 27 grammar categories.
* **Schema Shape:**
  ```python
  GRAMMAR_QUESTIONS = {
      "Articles: A, An, The": [
          {
              "prompt": "Choose the correct article...",
              "options": ["A", "An", "The", "—"],
              "answer": "An",
              "explanation": "Use 'an' before words that start with a vowel sound."
          }
      ]
  }
  ```
* **Status:** Appears to be repository-authored educational content, but lacks an explicit source and copyright header. Safe for private local evaluation, but held for rights confirmation before commercial distribution.

### 5.6 Built-in Sample Course Catalog (Fail-Closed Quarantine)
* **Path:** [`backend-service/app/core/sample_data_catalog.py`](../../backend-service/app/core/sample_data_catalog.py) (28,912 bytes)
* **Metrics:** 486 lines; 4 achievements, 2 course categories, 2 A1 courses (2 units, 4 lessons, 40 interactive exercises).
  - Course 1: *English Grammar Foundations* (1 unit: "Present Simple Basics", 2 lessons: "I/You/We/They + Verb" [10 exercises], "He/She/It + Verb-s" [10 exercises]).
  - Course 2: *Daily Vocabulary Starter* (1 unit: "Home and Family", 2 lessons: "Family Members" [10 exercises], "Rooms and Objects" [10 exercises]).
* **Entrypoint:** [`backend-service/scripts/seed_courses_directly.py`](../../backend-service/scripts/seed_courses_directly.py); [`backend-service/app/services/admin_seed_service.py`](../../backend-service/app/services/admin_seed_service.py).
* **Governance Status:** `unverified` / `hold_pending_rights` (Uncataloged in manifest).
* **Fail-Closed Rationale:** `sample_data_catalog.py` is not explicitly cataloged as an approved artifact in [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json). The catalog includes external Unsplash thumbnail URLs (`images.unsplash.com`), Vietnamese translations, and educational exercise questions lacking an explicit source-specific rights manifest or tracked license approval. In strict accordance with the independent development governance, it is classified fail-closed and held pending formal rights verification and manifest amendment.

---

## 6. Catalog Reconciliation Ledger

This section demonstrates complete reconciliation against the pre-existing project ledgers and catalogs.

### 6.1 Reconciliation with `LOCAL_DATA_PROVENANCE_MANIFEST.json`
Every source, artifact, and seed entrypoint declared in [`docs/LOCAL_DATA_PROVENANCE_MANIFEST.json`](../LOCAL_DATA_PROVENANCE_MANIFEST.json) is fully accounted for in this inventory:

| Manifest Source ID | Manifest Status | Inventory Reconciliation Status | Path Citation |
|---|---|---|---|
| `source-repository-mit` | `repository_license_only` | `repository_license_only` (Software license only, not content license) | [`LICENSE`](../../LICENSE) |
| `source-repository-authored-seed` | `repository_license_only` | `repository_license_only` (Minimal local seed candidate) | [`backend-service/app/core/shop_catalog.py`](../../backend-service/app/core/shop_catalog.py) |
| `source-synthetic-demo-personas` | `synthetic` | `synthetic` (Minimal local seed candidate) | [`backend-service/scripts/seed_demo_data.py`](../../backend-service/scripts/seed_demo_data.py); [`backend-service/scripts/seed_analytics.py`](../../backend-service/scripts/seed_analytics.py) |
| `source-test-fixture-declarations` | `fixture_only` | `fixture_only` (Test only, never runtime seeded) | [`contracts/content-agent/fixtures/*`](../../contracts/content-agent/fixtures); [`ai-service/tests/content_etl/fixtures/*`](../../ai-service/tests/content_etl/fixtures) |
| `source-unattributed-repository-content` | `unverified` | `unverified` (Held pending written rights) | [`ai-service/data/sample_stories.json`](../../ai-service/data/sample_stories.json); [`ai-service/data/kg/*.json`](../../ai-service/data/kg); [`scripts/categorized_words_final.json`](../../scripts/categorized_words_final.json) |
| `source-external-rss-feeds` | `blocked_external` | `blocked_external` (Prohibited from Demo Pack v1) | [`backend-service/scripts/seed_empty_tables_and_crawl.py`](../../backend-service/scripts/seed_empty_tables_and_crawl.py) |

*Note: `backend-service/app/core/sample_data_catalog.py` is not cataloged in `LOCAL_DATA_PROVENANCE_MANIFEST.json` and is classified fail-closed as `unverified` (`hold_pending_rights`).*

### 6.2 Reconciliation with `LOCAL_PARITY_JOURNEY_LEDGER.md`
This inventory directly maps to the active parity journey requirements:
* **Journey J-01 (Bootstrap DB):** Satisfied cleanly by [`backend-service/scripts/bootstrap_local.py`](../../backend-service/scripts/bootstrap_local.py).
* **Journey J-02 (Seed Minimal Shop Catalog):** Satisfied cleanly by [`backend-service/app/core/shop_catalog.py`](../../backend-service/app/core/shop_catalog.py) via [`backend-service/scripts/seed_shop_items.py`](../../backend-service/scripts/seed_shop_items.py).
* **Journey J-03 (Synthetic Personas):** Satisfied cleanly by [`backend-service/scripts/seed_demo_data.py`](../../backend-service/scripts/seed_demo_data.py) and [`backend-service/scripts/seed_analytics.py`](../../backend-service/scripts/seed_analytics.py).
* **Journeys J-04, J-05, J-06 (Learning Paths & Stories):** Journey J-04 remains `UNVERIFIED` because `sample_data_catalog.py`, `sample_stories.json`, and `categorized_words_final.json` are not approved learning content in `LOCAL_DATA_PROVENANCE_MANIFEST.json` and are held pending rights approval.
* **Journeys J-07 (RSS Feeds) & J-08 (Anki Decks):** Confirmed `INTENTIONALLY_DISABLED` and prohibited from Demo Pack v1.
* **Journey J-09 (IELTS Practice):** Confirmed `UNVERIFIED` and held pending listening audio synthesis and rights verification.

---

## 7. Quality Gates & Verification Evidence

All quality gates defined in the Wave A1 task dispatch have been verified:

### 7.1 Command Validation Log (Reproducibility)
The byte counts, record counts, and schema shapes reported in this document were computed using repository-local inspection utilities. The following PowerShell commands reproduce these metrics:

```powershell
# 1. Verify byte sizes of core seed catalogs
Get-Item LICENSE, backend-service/app/core/shop_catalog.py, backend-service/app/core/sample_data_catalog.py | Select-Object FullName, Length

# 2. Verify byte sizes of large data files
Get-Item scripts/categorized_words_final.json, ai-service/data/sample_stories.json, backend-service/scripts/ielts_paper_academic_1.py | Select-Object FullName, Length

# 3. Verify total KG files in ai-service/data/kg
Get-ChildItem ai-service/data/kg/*.json | Measure-Object -Property Length -Sum

# 4. Verify git status and ensure diff is strictly isolated
git status --short
git diff --check docs/demo-data/source-inventory-v1.md
```

### 7.2 Strict Network & Safety Isolation
* **Zero Network Requests:** No HTTP/HTTPS request, socket connection, or DNS lookup was performed.
* **Zero Database Mutations:** No PostgreSQL, MongoDB, Redis, or Kuzu databases were modified or connected to.
* **Zero Secret Leakage:** No `.env` or configuration secrets were read or logged.
* **Exclusive Output Path:** All changes by this task are strictly confined to [`docs/demo-data/source-inventory-v1.md`](source-inventory-v1.md). Existing dirty worktree modifications were completely preserved.
