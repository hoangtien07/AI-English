# Local parity journey ledger

Status is intentionally limited to `PASS`, `INTENTIONALLY_DISABLED`,
`UNVERIFIED`, and `OUT_OF_SCOPE`. A checked-in test source, implementation
claim, or historical generated report is not a `PASS`; the status changes only
when there is a completed, local, independent run with the listed evidence.

This ledger uses repository-local evidence only. No original deployment, user
data, external website, RSS feed, API, or third-party dataset was accessed for
this inventory. The 2026-09-08 validation record adds strong service-level
evidence; it does not convert a service test into a browser/mobile journey.

## Evidence boundary

The final local report records passing current-tree checks: backend focused
17 passed and full isolated 1679 passed/3 skipped, AI clean image/health and
feature gates, admin build/tests, Flutter configuration tests, data-manifest
tests, and local developer commands. Those checks prove their named
service/configuration behavior only. No complete learner or administrator UI
journey has independently completed every listed acceptance step, so this
ledger records no new `PASS` result.

| Journey ID | Local journey | Status | Repository-only evidence | Next dependency |
|---|---|---|---|---|
| J-01 | Bootstrap an empty database and restart an Alembic-managed database without loss | UNVERIFIED | Isolated backend runner created/removed only a UUID-named `*_test` DB and full suite passed (1679 passed, 3 skipped); focused closure coverage also passed. This is not an independently observed restart journey. | Capture a redacted empty-then-restart acceptance run with migration/version and persistence observations. |
| J-02 | Seed the minimal shop catalog twice without duplicates | UNVERIFIED | Focused backend closure gate passed; `seed_shop_items.py` updates/inserts by item name. The final evidence does not record the two observed production-like seed counts as a journey. | Capture the two-run local seed acceptance output/counts after J-01. |
| J-03 | Create synthetic dashboard/demo personas without touching real users | UNVERIFIED | `seed_demo_data.py` deletes only `demo_%@lexilingo.dev`; `seed_analytics.py` scopes cleanup to test/demo namespaces. These are clearly synthetic personas but have no current run report. | Use an isolated database, run each script, and verify namespace-scoped cleanup plus foreign-key counts. |
| J-04 | Browse a local course/vocabulary learning path from repository learning content | UNVERIFIED | Learning/content models and multiple seed/import scripts exist, but `categorized_words_final.json`, KG JSON, and story blueprints lack per-artifact rights records. | Owner must approve a local content pack with source, license, attribution, checksum, and allowed use before it is seeded. |
| J-05 | Start an AI story conversation backed by `sample_stories.json` | UNVERIFIED | AI image rebuild, healthy container, and Gemini chat/SSE service gates passed, but no approved story-content seed plus end-to-end story UI acceptance was recorded. | Resolve J-04 rights decision, then capture approved Mongo seed and AI-to-UI story acceptance evidence. |
| J-06 | Run voice/STT/TTS learning interaction | UNVERIFIED | AI service gates passed for Piper TTS, HuBERT, and STT (138 worker + 15 gate tests); real-fixture STT output was non-empty at about 1.4 s load/1.2 s transcription with a 51,441,771-byte cache. No complete Flutter/web voice-learning interaction was exercised. | Capture an independent UI-to-service voice journey using owned/local-safe configuration. |
| J-07 | Receive external news/RSS content transformed into lessons | INTENTIONALLY_DISABLED | `seed_empty_tables_and_crawl.py` declares external RSS sources; the active plan explicitly blocks external acquisition until a written rights decision. | Written source-by-source rights decision covering terms, license, retrieval, transformations, storage, attribution, and deletion/refresh policy. |
| J-08 | Import an externally supplied Anki vocabulary deck | INTENTIONALLY_DISABLED | `seed_vocab_from_anki.py` accepts an operator-provided `.apkg`; the repository does not include an approved deck or its license record. | Owner supplies a specific authorized deck and a provenance record; validate the copied fields and attribution before import. |
| J-09 | Seed the bundled IELTS practice paper as a publishable assessment | UNVERIFIED | `seed_ielts_test.py` is idempotent by title but leaves the paper unpublished when listening audio is absent; no source-specific rights record or completed seed/publish-gate report is tracked. | Rights decision for paper text plus owned/authorized audio and a completed admin publish-gate run. |
| J-10 | Use external provider integrations (Firebase/OAuth/SMTP) in local parity | INTENTIONALLY_DISABLED | Flutter configuration/Firebase focused tests passed, but owned Firebase registration/configuration/service-account details remain incomplete and SMTP is undecided. These integrations remain intentionally disabled rather than proven. | Complete owned app registrations/origins, approve the super-admin allowlist, choose SMTP, then run negative and lifecycle integration tests. |
| J-11 | Exercise hosted/mobile-store behavior | OUT_OF_SCOPE | The active plan is local-only and explicitly defers staging, production, hosting, and mobile-store scope. | Pass local core, AI, and parity gates before opening the deferred delivery/rebrand work. |

## Rights decisions required before external acquisition

1. For each proposed source, record the exact dataset/feed/page, rights holder,
   license/terms version, allowed commercial/derivative/redistribution use,
   attribution text, access method, retrieval date, checksum, and intended
   fields/transformations.
2. Confirm that source terms permit automated retrieval and the intended stored
   derivative content. A public URL, a test fixture, or a repository mention is
   not authorization.
3. Obtain explicit approval before importing Anki decks, RSS/news, copyrighted
   IELTS material, captions/audio, or any source represented in existing graph
   artifacts. Do not copy original-site accounts, progress, chats, emails,
   tokens, or private media.
4. After approval, add a source-specific manifest entry and a reproducible
   idempotent importer before enabling its journey. Preserve required notices
   with the produced records and retain a redacted validation report.

## Catalog contract

`LOCAL_DATA_PROVENANCE_MANIFEST.json` is the durable machine-readable companion
to this ledger. Its validation test checks required fields, controlled status
values, duplicate IDs, paths, and every artifact/entrypoint foreign-key
reference. It is a catalog of evidence and constraints, not a declaration that
unverified repository content is licensed for deployment.
