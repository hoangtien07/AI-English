# AI-English Independent Development Plan

> Living plan for taking independent ownership of the LexiLingo-derived codebase.
> Every agent working on this effort must read this file and `AGENTS.md` before making changes.

## Document control

| Field | Value |
|---|---|
| Status | Active |
| Current focus | Independent repository metadata and upstream-import controls; integration gates remain open |
| Current phase | Independent clean snapshot; local integration/account decisions remain |
| Last updated | 2026-09-09 |
| New repository | `https://github.com/hoangtien07/AI-English.git` |
| Upstream reference | `https://github.com/InfinityZero3000/LexiLingo.git` (fetch only) |
| Owned domain | `hoangtien07.me` |
| Working product name | AI-English |
| Rebrand strategy | Option B — full rebrand, detailed plan deferred until local is healthy |
| Hosting decision | Deferred; discuss before choosing a paid service |

## 1. Purpose

Build an independently owned version of the system that:

1. Runs locally without depending on the original author's deployments, accounts, databases, secrets, or domains.
2. Reaches functional parity with the useful behavior of the original deployed application for the first release.
3. Uses only data and third-party services that the new owner is authorized to use.
4. Can later be promoted through staging to production under `hoangtien07.me`.
5. Can be resumed safely by another agent using the task ledger and exit gates in this document.

## 2. Decisions already made

- [x] The owned GitHub repository is `hoangtien07/AI-English`.
- [x] The original repository remains available as a read-only `upstream` remote.
- [x] Local development is the only active delivery phase.
- [x] Staging and production requirements remain recorded but are not active.
- [x] Full rebranding is selected, but its detailed execution plan begins only after the local parity gate passes.
- [x] `hoangtien07.me` is available for later staging/production use.
- [x] Free hosting is preferred for a 1–2 user demo.
- [x] No paid hosting may be selected or purchased without discussing the measured resource need and options with the owner.
- [x] A fresh independent data store is the default. No original user or production data may be copied.
- [x] The clean snapshot replaces any history-rewrite plan. `origin` uses an independent orphan history; the upstream bridge stays local and private.
- [x] Firebase CLI authentication is available; the sole owned Web app **AI English Web** is registered in `english-5d522`, and its public Web SDK configuration is installed.
- [x] Gmail credentials remain only in ignored `backend-service/.env`; an `EHLO -> STARTTLS -> AUTH -> NOOP` probe passed without sending mail or exposing credentials.

## 3. Critical rules

### 3.1 Independence rules

- Never call `api.lexilingo.me`, `ai.lexilingo.me`, or another original deployment from a local development build.
- Never use credentials whose ownership is unknown, even if they are present in a local `.env` file.
- Never deploy with the original Firebase project `lexilingo-88492` or its Google OAuth clients.
- Never connect to an original Supabase, PostgreSQL, MongoDB, Redis, Firebase, Vercel, Render, Cloudflare, SMTP, RevenueCat, Sentry, or API-provider account.
- Production configuration must fail closed if a required owned value is missing. It must not fall back to the original author's domain.
- Preserve the MIT copyright and permission notice in `LICENSE`.

### 3.2 Data acquisition rules

The public site `https://www.lexilingo.me/?v=2` may be studied for public behavior and UX parity, but public visibility does not automatically grant permission to copy its data.

Before any automated collection:

1. Identify the exact dataset and why it is needed.
2. Check the site's terms, robots policy, response headers, and any displayed license.
3. Determine whether the source is authored content, third-party licensed content, or user data.
4. Prefer repository seed files, openly licensed upstream datasets, or synthetic data.
5. Record source URL, license, retrieval date, transformation, and checksum in a provenance manifest.
6. Do not bypass authentication, rate limits, access controls, or bot protection.
7. Do not copy accounts, personal data, progress, chats, emails, tokens, or private media.
8. Stop and request owner approval when rights are unclear.

### 3.3 Change-management rules

- Do not push to `upstream`; its push URL must remain disabled.
- Do not merge unrelated histories or push upstream refs. Import upstream changes only under `docs/UPSTREAM_SYNC_POLICY.md`.
- Do not overwrite unrelated working-tree changes. At plan creation, these files were already modified:
  - `flutter-app/analysis_options.yaml`
  - `flutter-app/pubspec.lock`
- Use one focused branch/PR per milestone.
- Update this file after completing a task: checkbox, status table, evidence, and change log.
- Run the required test suite before marking a gate complete.
- Use the test-writer after feature/bug-fix implementation and security-reviewer for auth, CORS, environment, secret, or deployment changes, as required by `AGENTS.md`.
- Use code-reviewer before a PR is declared ready.

## 4. Verified baseline on 2026-09-05

### 4.1 Repository ownership

```text
origin             https://github.com/hoangtien07/AI-English.git (fetch/push)
upstream           https://github.com/InfinityZero3000/LexiLingo.git (fetch)
upstream           DISABLED (push)
integration branch hoangtien07/lexilingo-clean-v1 -> origin/main
```

The owned repository is the only approved push target. First-push authorization
and gate evidence are tracked in Section 15; staging, production, and hosting
remain deferred.

### 4.2 Original live endpoints

Observed during planning:

| Endpoint | Observation |
|---|---|
| `https://www.lexilingo.me` | HTTP 200 |
| `https://lexilingo.me` | HTTP 404 |
| `https://admin.lexilingo.me` | HTTP 200 |
| `https://api.lexilingo.me/health` | Timed out; an earlier preflight returned Cloudflare 522 |
| `https://ai.lexilingo.me/health` | DNS did not resolve |

These endpoints are reference-only and must not be runtime dependencies.

### 4.3 Local toolchain

- Docker Desktop and Docker Compose are available.
- Flutter is available.
- Bash is available.
- `docker-compose.dev.yml` passes `docker compose config --quiet`.
- PostgreSQL, MongoDB, Redis, backend, and AI containers have previously been created locally.

### 4.4 Confirmed local blockers

| ID | Blocker | Evidence | Required correction |
|---|---|---|---|
| BLK-001 | Flutter development config calls production | `flutter-app/assets/env/dev_config` | Use loopback API/AI URLs and no production fallback |
| BLK-002 | Flutter web uses a random port through `make run-web` | `Makefile` | Standardize on `localhost:8080` |
| BLK-003 | Backend Uvicorn worker crashes while the container remains running | Pydantic `SettingsError` for `ALLOWED_HOSTS` | Correct comma-separated environment parsing and health reporting |
| BLK-004 | AI service cannot import `service` | `ModuleNotFoundError: No module named 'service'` | Copy/mount `ai-service/service` and add a build import check |
| BLK-005 | AI container is unhealthy | Docker health state | Resolve BLK-004, then inspect subsequent startup dependencies |
| BLK-006 | Firebase identifiers belong to the original project | Tracked Firebase options, web worker, and `firebase.json` | Replace with owned project; use placeholders until created |
| BLK-007 | Runtime defaults point to the original domains | Flutter, admin, backend, gateway, deploy scripts, CI | Introduce an environment contract and fail closed |
| BLK-008 | Current CD deploys both `main` and `dev` with Vercel `--prod` | `.github/workflows/cd.yml` | Separate preview/staging/production pipelines before any hosted deployment |
| BLK-009 | Current CD builds only the backend image | `.github/workflows/cd.yml` | Later add AI image and actual controlled deployment |

### 4.5 Coupling inventory

Runtime/source configuration currently includes at least:

- 25 files referencing `api.lexilingo.me`.
- 39 files referencing `lexilingo.me`.
- 11 files referencing the original Firebase project or sender ID.
- 13 files referencing `com.lexilingo` package/bundle identifiers.
- 10 files referencing the original GitHub owner.

Historical documentation, tests, migrations, and the MIT notice must be reviewed separately from runtime configuration; not every historical reference should be mechanically replaced.

## 5. Target local architecture

```text
Flutter Web http://localhost:8080
        |
        +--> Backend http://127.0.0.1:8000/api/v1
        |       +--> PostgreSQL :5432
        |       +--> Redis :6379
        |
        +--> AI http://127.0.0.1:8001/api/v1
                +--> MongoDB :27017
                +--> dedicated Redis inside Compose network
                +--> owned cloud LLM key or local Ollama, selected explicitly
```

Local success must not require DNS, TLS, Vercel, Render, Cloudflare, or the original website.

## 6. Local environment contract

### 6.1 Public Flutter development configuration

```env
ENVIRONMENT=development
API_BASE_URL=http://127.0.0.1:8000/api/v1
API_BASE_URL_FALLBACK=
AI_SERVICE_URL=http://127.0.0.1:8001/api/v1
AI_SERVICE_URL_FALLBACK=
VOICE_DUPLEX_ENABLED=false
DEBUG_MODE=true
```

No server secret may appear in a Flutter asset.

### 6.2 Backend development requirements

Required locally:

- `APP_ENV=development`
- `DATABASE_URL` pointing to the Compose PostgreSQL service
- a new development-only `SECRET_KEY`
- `ENABLE_APP_CORS=true`
- `ALLOWED_ORIGINS=http://localhost:8080`
- `ALLOWED_HOSTS=localhost,127.0.0.1`
- `REDIS_URL` pointing to the Compose Redis service
- `AI_SERVICE_URL=http://ai-service:8001/api/v1`

Optional until their feature milestones:

- Firebase credentials and project ID
- Google OAuth client IDs
- SMTP settings
- content API keys
- RevenueCat key
- Sentry DSN

### 6.3 AI development requirements

Required for service startup:

- `ENVIRONMENT=development`
- independent `SECRET_KEY`/service tokens where required
- `MONGODB_URI=mongodb://mongodb:27017`
- Redis configuration pointing to the AI Redis service
- `BACKEND_SERVICE_URL=http://backend-service:8000`
- local CORS origin `http://localhost:8080`

At least one inference mode must be selected explicitly:

1. Owned Gemini/Groq API key; easiest for feature-parity development.
2. Local Ollama; avoids provider cost but needs sufficient RAM/CPU/disk.
3. AI-disabled core mode; acceptable only until LOCAL-CORE, not LOCAL-PARITY.

Unknown existing API keys must not be reused.

## 7. Local execution plan, reconciliation ledger, and waves

### 7.1 Final reconciliation rules (2026-09-08)

This is the authoritative final reconciliation of every original `L0-01`
through `L6-07`. Every item uses exactly one final status: `DONE`,
`SUPERSEDED`, `BLOCKED`, or `NOT DONE`. `DONE` requires the evidence named in
the ledger; a source diff, test source, or historical claim alone is not proof.
`BLOCKED` requires a concrete external decision, account, or authorization;
`NOT DONE` is remaining work without such a blocker.

The final command record is `docs/LOCAL_VALIDATION_REPORT.md`; it contains
outcomes, paths, checksums, counts, and timings but no secret values. Service
and API gates do not prove browser/mobile UI journeys, which remain separately
governed by `LOCAL_PARITY_JOURNEY_LEDGER.md`.

Earlier documentation-only reconciliation/orchestration attempts that reported
missing final evidence are **SUPERSEDED as evidence collection attempts**, not
as deliverables. Their conservative statuses change only where a later final
gate supplied proof; a failed/incomplete attempt cannot make a deliverable pass
or fail.

### 7.2 Current decisions and blockers

| Decision or blocker | Final record | Consequence |
|---|---|---|
| Local SMTP | Owned Gmail with an App Password is approved and configured locally. | Authentication/transport probe passed; an actual transactional-email delivery remains a separate end-to-end check. |
| Firebase / service account | The owned Web app and public SDK config are complete for Web-only scope. | Google provider/support email and local authorized domains still require Firebase Console confirmation; no service-account secret belongs in Flutter. |
| Admin authorization | The owner approved one exact super-admin email and the normalized allowlist tests passed. | Keep privileges exact-address only; never grant a whole domain. |
| External content | The owner states they have permission to copy and reuse the official-site content for the demo. | Acquisition/import remains unimplemented and must retain provenance; later course content will be teacher-authored independently. |
| Repository history | Independent clean snapshot is the approved replacement for a history rewrite. | Preserve the orphan `origin` history; use the local/private upstream bridge only for reviewed imports. |
| Delivery scope | Rebrand, staging, production, hosting, and mobile remain deferred. | The independent clean snapshot and local integration commits are in scope; no deploy, purchase, or hosted/mobile parity claim is made. |

### 7.3 Task ledger

#### LOCAL-0 - ownership, safety, and baseline

| ID | Final status | Evidence or remaining condition |
|---|---|---|
| L0-01 | DONE | `git remote -v` shows `origin` at the owned repository. |
| L0-02 | DONE | `git remote -v` and configured push URL show upstream push is `DISABLED`. |
| L0-03 | DONE | Independent clean snapshot root commit `ba243ba3881321efcbea0e68f8466ad072ac0843` replaces reachable-history remediation. Current-tree sentinel and `git diff --check` remain required for imports. |
| L0-04 | DONE | Independent security re-review approved the current tree for `origin` only: the narrow Firebase Web public-config rule, Google fail-closed behavior, Facebook disablement, tracked-secret checks, and disabled upstream push all passed. |
| L0-05 | DONE | Final integration evidence includes sentinel 15/15, backend auth/config/email 92/92, Flutter Firebase 10/10, Flutter Web build, Compose static config, plan 52/52, and clean diff/worktree checks. Flutter analysis has 13 recorded non-fatal baseline warnings. |
| L0-06 | DONE | The owner explicitly authorized the first push on 2026-09-09; the final current-tree security and integration gates passed. Push execution is tracked in Section 15. |

`GATE-OWNERSHIP` passed: repository ownership, explicit owner authorization,
current-tree security review, and integration evidence are all recorded.

#### LOCAL-1 - configuration isolation

| ID | Final status | Evidence or remaining condition |
|---|---|---|
| L1-01 | DONE | Flutter focused configuration/Firebase tests: 5 passed; local stack commands succeeded. |
| L1-02 | DONE | Focused Flutter configuration tests passed and the current-tree sentinel rejects legacy runtime coupling. |
| L1-03 | DONE | Admin build/tests and the sentinel passed with fail-closed deployable configuration. |
| L1-04 | DONE | `dev-local.ps1 up-core`, `up-full`, and `status` passed against the local Compose contract. |
| L1-05 | DONE | Admin build/tests passed against the local configuration. |
| L1-06 | DONE | `scripts/security/verify_independent_config.py` and `git diff --check` passed. |
| L1-07 | DONE | Flutter focused configuration/Firebase suite: 5 passed; analysis reported 13 warnings and no errors. |

`GATE-CONFIG-ISOLATED` is proven for current local configuration, not for unregistered external-provider accounts.

#### LOCAL-2 - backend core

| ID | Final status | Evidence or remaining condition |
|---|---|---|
| L2-01 | DONE | Backend focused gate: 17 passed; Ruff passed; full isolated suite: 1679 passed, 3 skipped. |
| L2-02 | DONE | Compose configuration passed and the local core stack reached healthy status. |
| L2-03 | DONE | Actual `up-core` and `status` completed successfully. |
| L2-04 | DONE | Focused backend gate includes the current auth/CORS checks (17 passed). |
| L2-05 | DONE | Isolated runner created and removed only a UUID-named `*_test` database; the full suite passed. |
| L2-06 | DONE | Focused backend gate passed, including local seed/bootstrap closure checks. |
| L2-07 | DONE | Focused backend lifecycle gate passed; this is API/service evidence, not a Flutter UI journey. |
| L2-08 | DONE | Prior focused persistence gate passed; it proves the tested service persistence path only. |

`GATE-LOCAL-CORE` is proven at the tested local service/API scope. Browser learner journeys remain separately unverified.

#### LOCAL-3 - AI service

| ID | Final status | Evidence or remaining condition |
|---|---|---|
| L3-01 | DONE | Clean AI image rebuilt successfully; Moonshine wheel checksum verification passed. |
| L3-02 | DONE | Compose configuration passed and the rebuilt AI service was healthy. |
| L3-03 | DONE | Clean rebuild completed successfully. |
| L3-04 | DONE | Rebuilt AI container reached healthy state. |
| L3-05 | DONE | Owned Gemini was selected for local parity; do not record its credential in this plan. |
| L3-06 | DONE | Prior focused persistence gate passed for the tested AI persistence path. |
| L3-07 | DONE | Gemini chat/SSE, Piper TTS, HuBERT, and STT gates passed: 138 STT worker tests plus 15 gate tests; real-fixture smoke returned non-empty output after about 1.4 s load and 1.2 s transcription, with a 51,441,771-byte cache. |
| L3-08 | NOT DONE | Timings and cache size are useful observations, but no controlled RAM/CPU/disk resource benchmark exists. |

`GATE-LOCAL-AI` is proven for listed service features, not for a complete voice-learning UI journey or hosting capacity.

#### LOCAL-4 - owned integrations

| ID | Final status | Evidence or remaining condition |
|---|---|---|
| L4-01 | DONE | Firebase CLI access was verified and the sole owned Web app **AI English Web** was created in project `english-5d522`. |
| L4-02 | DONE | Web-only registration and generated public SDK configuration are installed; no Android/iOS app or private service-account material was created. |
| L4-03 | BLOCKED | Firebase Console must still enable the Google provider/support email and confirm `localhost` plus `127.0.0.1` as authorized domains. |
| L4-04 | DONE | Web SDK identifiers are wired through the fail-closed bootstrap and service-worker gates; 10 focused Flutter tests and the Web build passed. |
| L4-05 | DONE | The owner selected Gmail, approved the exact sender/super-admin address, and the App Password remains only in ignored `backend-service/.env`. |
| L4-06 | NOT DONE | SMTP `EHLO`, STARTTLS, authentication, and NOOP passed without sending mail; actual register/reset delivery and link handling have not yet been smoke-tested end to end. |
| L4-07 | NOT DONE | Mobile-store work is deferred and has no local acceptance evidence. |
| L4-08 | NOT DONE | Optional production integration is deferred. |
| L4-09 | NOT DONE | The owner confirmed reuse rights for the official-site demo content; source mapping, provenance controls, and an idempotent importer remain to be implemented. |

`GATE-LOCAL-INTEGRATIONS` remains open only for Firebase Console/Google sign-in
validation and an end-to-end transactional-email delivery smoke. Provider
configuration and transport-level evidence do not prove those browser journeys.

#### LOCAL-5 - sample data and behavioral parity

| ID | Final status | Evidence or remaining condition |
|---|---|---|
| L5-01 | DONE | `LOCAL_DATA_PROVENANCE_MANIFEST.json` validation: 5 passed. It inventories constraints; it does not grant content rights. |
| L5-02 | DONE | `LOCAL_PARITY_JOURNEY_LEDGER.md` is the current journey ledger and identifies its evidence boundary. |
| L5-03 | DONE | The owner recorded that they have the right to copy and reuse official-site content for this demo; provenance and demo-only boundaries still apply. |
| L5-04 | NOT DONE | Source inventory, schema mapping, rate-safe acquisition, and an idempotent importer have not been implemented. |
| L5-05 | BLOCKED | Requires a selected and authorized seed pipeline. |
| L5-06 | BLOCKED | Requires populated selected seeds from L5-04/L5-05. |
| L5-07 | BLOCKED | Requires the minimal seed schema/pipeline; personas must be synthetic. |

`GATE-LOCAL-PARITY` remains open. Do not infer data rights from public visibility, and do not copy personal data.

#### LOCAL-6 - local developer experience

| ID | Final status | Evidence or remaining condition |
|---|---|---|
| L6-01 | DONE | PowerShell `dev-local.ps1` interface passed Pester: 9/9. |
| L6-02 | DONE | Actual `up-core` and `up-full` succeeded. |
| L6-03 | DONE | Pester 9/9 covers the local command/environment contract without displaying values. |
| L6-04 | DONE | Actual startup commands waited for health successfully; `status` succeeded. |
| L6-05 | DONE | `status` passed; the script also provides `stop` while preserving volumes. |
| L6-06 | DONE | Pester covers explicit `reset-data` confirmation/safety behavior. |
| L6-07 | DONE | Root `README.md` documents the final `dev-local.ps1` interface, prerequisites, health behavior, profiles, tests, and explicit reset contract. |

### 7.4 Dependency DAG and executable waves

```text
W0 evidence/safety: L0-04 + L0-05 -> GATE-OWNERSHIP -> L0-06 (owner approval)

W1 config closure: verify L1-01..L1-05 -> L1-06 + L1-07 -> GATE-CONFIG-ISOLATED

W2 backend core: verify L2-01..L2-03 -> L2-04 -> L2-05 -> L2-06 -> L2-07 -> L2-08 -> GATE-LOCAL-CORE

W3 AI core: verify L3-01 + L3-02 -> L3-03 -> L3-04 -> L3-06 -> L3-07 -> L3-08 -> GATE-LOCAL-AI
             L3-05 is complete and supplies the provider decision; credentials remain local-only.

W4 integrations: L4-02 -> L4-04; DEC-MAIL-001 -> L4-05 -> L4-06

W5 data/parity: L5-01 + L5-02 + L5-03 -> L5-04 -> L5-05 -> L5-06 + L5-07 -> GATE-LOCAL-PARITY

W6 developer experience: GATE-CONFIG-ISOLATED + GATE-LOCAL-CORE + GATE-LOCAL-AI
                        -> L6-01 -> L6-02 + L6-03 + L6-04 -> L6-05 + L6-06 -> L6-07
```

All evidence-only waves through W3 are reconciled. The remaining executable
work is W0 owner approval/security evidence, W4 owner/account decisions, W5 rights and approved
data, and the L3-08 benchmark.
Staging, production, hosting selection, and rebrand execution are deferred and
are not active nodes in this local DAG.

### 7.5 Approved execution strategy and quality gates

- Sol is the lead, orchestrator, and gatekeeper.
- Sol delegates implementation through Orca to `codex gpt-5.6-terra` at high
  reasoning effort. Workers receive bounded, non-overlapping tasks and do not
  change a gate by assertion alone.
- Supervision is event-driven only: react to `worker_done`, escalation, or a
  blocking question; do not poll or babysit idle terminals.
- Before each new wave, record its scope, collect required tests, specialist
  review, and no-secret evidence, then reconcile its final status.
- Required gates are: ownership safety before push; configuration isolation
  before local integration smoke; backend and AI health before developer
  experience; rights/provenance before parity data; and local parity/resource
  evidence before any hosting or rebrand planning becomes active.

Final local commands should converge on a small interface such as:

```text
./scripts/dev-local.ps1 up-core
./scripts/dev-local.ps1 up-full
./scripts/dev-local.ps1 status
./scripts/dev-local.ps1 test
./scripts/dev-local.ps1 stop
./scripts/dev-local.ps1 reset-data   # explicit confirmation required
```

## 8. Configuration/accounts the owner must create

### Needed during local work

| Item | When | Cost expectation | Notes |
|---|---|---|---|
| New Firebase project | LOCAL-4 | Free tier likely sufficient for local/demo evaluation | Do not reuse `lexilingo-88492` |
| Google OAuth Web client | LOCAL-4 | Normally no direct cost | Configure localhost redirect/origin and later owned domain |
| SMTP sender or mail sandbox | LOCAL-4 | Start with a free/dev tier | Never use the original Gmail sender |
| LLM inference choice | LOCAL-3 | Free API quota or local compute first | Benchmark before paid decision |

### Not needed yet

- Vercel/Cloudflare Pages project.
- Production VPS.
- Production PostgreSQL/MongoDB/Redis.
- Paid monitoring.
- Apple Developer or Google Play accounts.
- RevenueCat production project.
- Production email provider.

For every owner-created account, an agent must provide the exact console steps and required values at the moment the related task becomes active. Credentials must be entered by the owner into ignored local files or the relevant secret store; they must not be pasted into chat or committed.

## 9. Hosting decision gate — deferred

No hosting provider is selected yet.

The decision will be made only after `L3-08` supplies measurements and `GATE-LOCAL-PARITY` identifies the enabled features.

### Options to compare later

1. **Hybrid, preferred starting point**
   - Static Flutter/Admin hosting.
   - One VPS running gateway, backend, AI, PostgreSQL, MongoDB, and Redis.
   - Best match for the current Compose-based repository.
   - Requires backup, patching, monitoring, and enough RAM for AI workloads.

2. **Managed data services plus a smaller application host**
   - Less database administration.
   - More external accounts and possible monthly minimums.
   - Useful if a free/low-cost VPS cannot safely hold databases and AI together.

3. **Cloud inference plus a small CPU host**
   - Avoids hosting local LLM/STT models.
   - Cost follows usage and provider quotas.
   - Often suitable for a 1–2 user demo if free quotas are sufficient.

4. **Fully self-hosted AI**
   - Maximum control and no per-request LLM fee.
   - Most likely to require paid RAM/CPU/GPU resources.

### Required discussion before spending

- Measured peak RAM/CPU/disk for the selected demo journeys.
- Whether STT/TTS and Ollama must run on the server or can use owned cloud APIs.
- Expected demo hours and sleep/cold-start tolerance.
- Backup storage and restore requirements.
- Acceptable monthly budget ceiling.
- Region/latency requirements for users in Vietnam.

## 10. Staging backlog — recorded, not active

Candidate domains, subject to the rebrand plan:

- `staging.hoangtien07.me` or `staging-app.hoangtien07.me`
- `staging-admin.hoangtien07.me`
- `staging-api.hoangtien07.me`

Requirements:

- [ ] Separate secrets from local and production.
- [ ] Separate databases or fully isolated database instances/namespaces.
- [ ] Staging CORS permits only staging web/admin origins.
- [ ] Preview deployments never receive production secrets.
- [ ] Email is captured or restricted to approved recipients.
- [ ] Migrations run as a controlled one-shot job.
- [ ] Smoke, integration, backup, and restore tests pass.
- [ ] Resource/cost telemetry is collected before production selection.

## 11. Production backlog — recorded, not active

Potential domain layout after rebranding:

- `app.hoangtien07.me`
- `admin.hoangtien07.me`
- `api.hoangtien07.me`

Requirements:

- [ ] Full rebrand plan complete.
- [ ] Owned DNS/TLS/WAF accounts.
- [ ] Production-only secrets and key-rotation record.
- [ ] Explicit CORS/host allowlists.
- [ ] No database, MongoDB, Redis, metrics, or admin port exposed publicly.
- [ ] Encrypted daily backup plus offsite copy.
- [ ] Successful restore rehearsal.
- [ ] Immutable image tags by commit SHA.
- [ ] Deployment approval and rollback path.
- [ ] Security review and production smoke test.
- [ ] No `dev` branch deployment with production credentials.
- [ ] Privacy policy, terms, contact, and data provenance updated for the new owner/brand.

## 12. Rebrand backlog — detailed plan deferred

After `GATE-LOCAL-PARITY`, create a separate rebrand plan covering:

- Product name, visual identity, logo, icons, and copy.
- Flutter Dart package name if desired.
- Android namespace/application ID and Kotlin package path.
- iOS/macOS bundle identifiers and signing.
- Web metadata, OpenGraph, favicon, manifest, and security.txt.
- Firebase app registrations and messaging worker.
- Universal Links/App Links and `.well-known` files.
- Email sender, subjects, templates, reset/verify links.
- OpenAPI metadata and repository/contact URLs.
- Legal/content URLs and schema identifiers.
- Docker/systemd/resource names where operationally useful.
- Migration strategy so rebranding does not corrupt local data.

## 13. Testing and review matrix

| Change area | Minimum verification | Required specialist review |
|---|---|---|
| Flutter URL/config | Config unit tests, `flutter test`, `flutter analyze` | Test writer; code reviewer |
| Backend settings/CORS/auth | Settings tests, preflight tests, auth smoke, backend `pytest` | Test writer; security reviewer; code reviewer |
| Database/migrations/seeds | Fresh DB, upgrade DB, two seed runs, integrity checks | Test writer; security reviewer for schema/security impact |
| AI Docker/runtime | Image build, import smoke, AI tests, health and feature smoke | Test writer; code reviewer |
| Firebase/OAuth/SMTP | Local integration test, negative auth cases, secret scan | Security reviewer; test writer; code reviewer |
| Deployment configuration | Compose validation, secret scan, staging smoke, rollback | Security reviewer; code reviewer |

No task is `DONE` merely because code was written. Evidence must be recorded.

## 14. Open decisions

| ID | Status | Decision | Recommended default |
|---|---|---|---|
| DEC-AI-001 | DONE | Local AI inference provider | Owned Gemini selected for local parity; benchmark Ollama separately if needed |
| DEC-DATA-001 | IN PROGRESS | Which exact datasets are needed from the original public site | Reuse is owner-authorized for the demo; inventory and importer design remain before acquisition |
| DEC-MAIL-001 | DONE | Development SMTP provider | Owned Gmail selected; ignored App Password plus STARTTLS authentication/NOOP probe verified without sending mail |
| DEC-MOBILE-001 | DEFERRED | Whether Android/iOS must be in the first hosted demo | Web-first until local parity, unless owner changes scope |
| DEC-HOST-001 | DEFERRED | Free vs paid hosting topology | Decide from measured resources and explicit budget discussion |

## 15. Agent handoff protocol

At the beginning of every continuation:

1. Read `AGENTS.md` and this file completely.
2. Query project memory and code graph first when those tools are available.
3. Run `git status --short` and do not disturb unrelated changes.
4. Confirm the active phase is local; do not start staging, production, or rebranding work early.
5. Select the smallest unblocked task IDs that form one coherent change.
6. Mark those tasks `IN_PROGRESS` before implementation.
7. Implement, test, and obtain required specialist reviews.
8. Mark tasks `DONE` only with evidence.
9. Add a change-log entry containing files, commands/tests, findings, and next task IDs.
10. Do not push, deploy, purchase, scrape, or create external resources without the authorization required for that action.

## 16. Change log

### 2026-09-05 — Plan initialized

- Changed local Git remote ownership:
  - `origin` now points to `https://github.com/hoangtien07/AI-English.git`.
  - original repository is `upstream` with push disabled.
- Recorded the local runtime failures for backend settings parsing and missing AI package.
- Recorded original-domain/Firebase/CI coupling.
- Locked active scope to local development.
- Deferred hosting selection, staging, production, and full rebrand execution.
- No application code was changed.
- No commit, push, deployment, scraping, or external account creation was performed.

### 2026-09-06 — Wave-1 plan reconciliation (documentation-only)

- Read this plan and `AGENTS.md`, then inspected the current worktree status,
  relevant implementation diffs, and available test evidence without changing
  feature, configuration, or test files.
- Reconciled all original `L0-01` through `L6-07` IDs in Section 7. Source
  changes are recorded as `IN_PROGRESS` unless their required verification and
  review evidence is present; no secret values were copied into this document.
- Recorded the owned-Gemini, owned-Firebase/OAuth, incomplete Firebase-app/
  service-account, undecided-SMTP, and unauthorized-external-data decisions.
- Added the Sol/Orca event-driven execution model, quality gates, final status
  mapping, and local-only dependency waves. Staging, production, hosting, and
  rebrand execution remain deferred.
- No tests were run by this reconciliation. Current source contains focused
  backend test additions, but no contemporaneous successful run was found.

### Superseded next executable wave (2026-09-06)

1. W0: `L0-03`, `L0-04`, and `L0-05` — produce the security scan, review
   classification, and baseline evidence without exposing values.
2. W1: verify and close the existing local configuration work in `L1-01`
   through `L1-05`, then implement `L1-06` and `L1-07`.
3. In parallel on non-overlapping files, verify the existing W2/W3 changes:
   `L2-01` through `L2-03` and `L3-01` through `L3-02`.

### 2026-09-08 — Final evidence reconciliation (documentation-only)

- Reconciled every original `L0-01` through `L6-07` row using only `DONE`,
  `SUPERSEDED`, `BLOCKED`, or `NOT DONE`; no original ID is omitted.
- Recorded final gates: independence sentinel and `git diff --check`; Compose
  config; backend focused 17 passed, isolated 1679 passed/3 skipped, and Ruff;
  AI rebuild/checksum/health/STT gates; admin build/tests; Flutter focused 5
  passed and analysis with 13 warnings/no errors; data manifest 5 passed; and
  Pester 9/9 plus actual `up-core`, `up-full`, and `status`.
- Created `LOCAL_VALIDATION_REPORT.md` with safe reproduction and status
  validation commands. It distinguishes service/API proof from full UI
  acceptance and records no secret values.
- Updated the parity ledger without promoting any UI journey to `PASS`: the
  collected STT/TTS/chat/persistence evidence is service-level only.
- Preserved user-owned worktree changes. No commit, push, deploy, scrape,
  account creation, or history rewrite occurred.

### 2026-09-09 — repository metadata and upstream policy

- Normalized active repository links and maintainer metadata to
  `https://github.com/hoangtien07/AI-English` while retaining upstream and MIT
  attribution.
- Recorded the independent orphan clean snapshot as the approved replacement
  for history rewriting, and added the local/private, fetch-only upstream
  import policy with provenance, review, secret-scan, and test gates.
- Recorded Firebase CLI authentication without claiming a Firebase Web app or
  any external activation. Recorded that the Gmail password is only in ignored
  `backend-service/.env`; a live mail probe remains an integration gate.

### 2026-09-09 — owned Web integration and first-push gate

- Registered exactly one Firebase Web app, **AI English Web**, in the owned
  project and installed only its public Web SDK identifiers.
- Added fail-closed Firebase initialization and service-worker consistency
  coverage; 10 focused Flutter tests and the Web build passed. Facebook Web
  sign-in remains hard-disabled.
- Verified Gmail SMTP through `EHLO`, STARTTLS, authentication, and NOOP using
  ignored local configuration. No email was sent and no credential was logged.
- Recorded the owner's explicit first-push approval and demo-content reuse
  authorization. Firebase Console Google-provider/domain validation and actual
  transactional-email delivery remain separate acceptance checks.

### 2026-09-09 — final pre-push security and integration gate

- Reconciled the Firebase Web public-client configuration with the secret
  sentinel using a narrow path/object/field allowlist; private OAuth,
  service-account, SMTP, provider-key, and private-key patterns remain blocked.
- Made learner Google authentication fail closed before token verification when
  its client ID is absent, and disabled Facebook authentication server-side
  before token or database processing. Added negative regression coverage for
  both learner and admin client-ID boundaries.
- Independent security re-review approved push to `origin` only. Final local
  checks passed: sentinel tests 15/15, repository sentinel, backend focused
  auth/config/email 92/92, Flutter Firebase 10/10, Flutter analysis with 13
  known non-fatal warnings, Flutter Web build, Compose development static
  configuration, plan 52/52, `git diff --check`, and a clean worktree.
- Full-module Ruff findings are pre-existing baseline debt; scoped checks found
  no new lint violation from the security fix or added regression test.
- Created `origin/main` from the gated clean snapshot at `22395082` and verified
  the remote ref matched the local integration HEAD. The unrelated legacy local
  `main` branch was preserved and was not rewritten or renamed.

### Next executable work

1. For future upstream updates, follow `docs/UPSTREAM_SYNC_POLICY.md`: fetch for
   inspection, import only reviewed commits/patches with provenance, rerun all
   gates, and push only to `origin`; never merge unrelated histories or push
   upstream refs.
2. Resolve `L4-03` and `L4-06`: complete Firebase Console Google-provider and
   authorized-domain setup, run a browser Google sign-in smoke, and verify one
   real transactional-email journey without recording credentials or tokens.
3. Resolve `L5-04` through `L5-07` and `L3-08`: source inventory/import,
   authorized data journeys, and a controlled resource benchmark. Local README
   acceptance in `L6-07` is complete.
