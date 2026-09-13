# Security Review — Wave C Open-Data Enrichment

**Scope reviewed (read-only):** `backend-service/scripts/import_approved_course_artifact.py`; the OER curriculum adapter, contract/registry additions, backend source enum; and `open-data-source-register-v1.{json,md}`.  This review treats an open licence as a licence assertion, not as evidence that a particular payload, origin, or transformation is trustworthy.

## Result

**Blocking findings: 0.  High findings: 3.  Medium findings: 3.  Low findings: 0.**

No production, test, configuration, database, or existing documentation file was changed during the review.

## Findings

### HIGH — The command's allowlist and pins are entirely caller-controlled

**Evidence.** The importer accepts the register path from the CLI at `backend-service/scripts/import_approved_course_artifact.py:252`, resolves and reads it as an arbitrary local JSON file at lines 265–268, and marks an entry approved solely when its content says `approved: true` or `status == "approved"` at lines 118–129.  It then accepts a manifest when its fields exactly match that same caller-supplied record at lines 160–176; neither the register nor a snapshot is signature-verified, repository-anchored, or compared with a trusted server-side authority.  The adapter's checksum has the same trust issue: it compares a checksum declared inside the untrusted snapshot with a hash computed from that snapshot at `ai-service/api/services/content_etl/adapters/oer_curriculum.py:80–103, 125–126`.

**Impact.** A user who can invoke the import command against a writable development database can make arbitrary content appear approved by supplying a matching, fabricated register and artifact.  This also defeats the stated deferred-source policy: `common_voice` remains an accepted backend source at `backend-service/app/schemas/content_agent.py:122–141`, and the importer does not restrict register `source_id` values to an immutable approved source set.  Checksums prove only self-consistency after an attacker has chosen both values; they do not establish provenance, publisher identity, content safety, or rights.

**Reproduction.** Inspect the three cited matching paths, or construct an artifact manifest and a register entry with identical `source_id/source_version/immutable_ref/raw_checksum/license_id/official_url`, `approved: true`, and permitted `allowed_usage`; `_validate_register` returns the caller-supplied manifest pin.  The existing unit-test fixture deliberately demonstrates this shape at `backend-service/tests/test_import_approved_course_artifact.py:17–30`.

**Remediation.** Do not accept an approval authority as a free CLI path.  Store a versioned, code-reviewed register in a controlled location (or verify a detached signature/key ID against a baked-in trust root), allow only exact stable source IDs, and bind the artifact's raw/normalized/root hashes to an approved snapshot record created by the ingestion pipeline.  Reject deferred sources such as Common Voice at this importer boundary even if other platform enums retain them for future work.

### HIGH — OER provenance bypasses hostname/path policy and can re-enable SSRF through the shared downloader

**Evidence.** `validate_source_url()` deliberately returns any credential-free HTTPS URL for OER at `ai-service/api/services/content_etl/registry.py:248–251`, before canonical path rules at lines 252–285.  The model-level checks likewise exclude OER from host allowlisting at `ai-service/api/services/content_etl/contracts.py:231–244` and `331–343`.  The shared downloader calls this validator before issuing requests (`ai-service/api/services/content_etl/downloader.py:69–94, 169–192`), so its otherwise useful public-IP/redirect checks are reachable with an unapproved OER hostname should this source ever be passed to it.

**Impact.** The code establishes a broadly reusable source name whose URL validation accepts attacker-selected public origins and paths.  That enables provenance spoofing now and creates a regression-prone SSRF/network-egress path if a later caller uses the generic downloader, despite comments saying OER is offline-only.

**Reproducible command and observed result.** From the repository root, this read-only command succeeded during review and printed `https example.invalid /arbitrary`:

```powershell
Push-Location ai-service
python -B -c "from api.services.content_etl.registry import validate_source_url; p=validate_source_url('oer_curriculum','https://example.invalid/arbitrary'); print(p.scheme, p.host, p.path)"
Pop-Location
```

**Remediation.** Make offline-only structural in the type/API: reject `oer_curriculum` in `SnapshotDownloader.download()` and require an approved local snapshot descriptor.  Retain a strict provenance host/path allowlist for its source URL (including canonical decoding checks), or remove the OER enum from generic ETL/download contracts until an end-to-end approved snapshot flow exists.

### HIGH — `--local-database` accepts any SQLite target, not a verified local development database

**Evidence.** `_require_local_database()` returns immediately for every URL whose scheme starts with `sqlite` at `backend-service/scripts/import_approved_course_artifact.py:198–211`.  It does not constrain the SQLite file path to a dedicated development directory, reject URI modes, resolve symlinks, or require an explicit development database identity; `--apply` then opens the configured session and writes within a transaction at lines 214–246.

**Impact.** The acknowledgement flag can be used with an arbitrary SQLite target configured through the runtime environment, including a file reached through a symlink, a shared/mounted production-like volume, or a SQLite URI mode.  The `settings.is_production` check is valuable but is not sufficient as a location/identity guard.

**Reproduction.** Static trace: a `sqlite`/`sqlite+aiosqlite` database URL follows the unconditional return at lines 203–205, then `main()` calls `_apply()` after only `--local-database` at lines 276–282.  No database was contacted in this review.

**Remediation.** Permit only a resolved, non-symlink database file below a dedicated application-owned development directory, with an explicit environment/profile allowlist and a fail-closed test for URI/query forms.  For PostgreSQL, retain loopback checking and additionally require an explicit dev database name/user or a separate `IMPORT_ALLOWED_DATABASE_FINGERPRINT` configured outside ordinary operator input.

### MEDIUM — Local file checks are vulnerable to symlink substitution / TOCTOU and have no trusted-root boundary

**Evidence.** `_local_json_path()` resolves and validates a path at `backend-service/scripts/import_approved_course_artifact.py:33–47`, but `_read_json()` reopens the resulting pathname at lines 50–57 and `_sha256()` opens it again at lines 60–65.  The function follows symlinks during `resolve(strict=True)` and does not retain an opened file descriptor, compare file identity, or require that the artifact/register reside under a controlled immutable directory.

**Impact.** An attacker able to change a selected path after validation can substitute artifact/register contents between validation, validation hashing, and apply.  In combination with the caller-controlled approval finding, this makes forensic checksum output unreliable.

**Remediation.** Open each input once using platform-safe no-follow semantics where available, use the opened descriptor for bounded read/hash, and compare file identity/stat information before use.  If this is an owner-operated tool, require files beneath an approved import staging root and reject symlink components rather than relying on filename extension.

### MEDIUM — Unbounded JSON/HTML parsing allows local resource exhaustion

**Evidence.** The importer reads full text and performs `json.loads()` without byte, nesting, item-count, or string-size limits at `backend-service/scripts/import_approved_course_artifact.py:50–57`; it subsequently walks every course/unit/lesson/vocabulary entry at lines 135–148.  The adapter similarly calls `read_bytes()` and decodes/parses the entire JSON or HTML input at `ai-service/api/services/content_etl/adapters/oer_curriculum.py:203–206, 281–295`, while accumulating every output record in a list at lines 219–278.

**Impact.** A large or deeply nested local input can exhaust memory/CPU before schema validation rejects it.  This is primarily a local operator/staging risk, but becomes a service DoS if these paths are later exposed through an upload/automation wrapper.

**Remediation.** Enforce a low, documented maximum snapshot/artifact byte size before reading; cap JSON depth, array lengths, heading/attribute/text lengths, and generated records; use streaming parsing where practical; and return a stable rejection rather than loading arbitrary-size input.

### MEDIUM — The published demo register cannot act as this importer's approval register

**Evidence.** The importer requires `source_id`, `source_version`, `immutable_ref`/`snapshot_id`/`ref`, `raw_checksum`, `license_id`, `official_url`, and `allowed_usage` at `backend-service/scripts/import_approved_course_artifact.py:93–129`.  `docs/demo-data/open-data-source-register-v1.json` uses `id`, `version_ref`, `sha256`, `attribution`, `permitted_fields`, and no `allowed_usage`; moreover its only curriculum source is expressly `blocked` (`docs/demo-data/open-data-source-register-v1.json:20–42`).  The OER adapter tests use `https://example.test` as the source origin (`ai-service/tests/content_etl/test_oer_curriculum.py:17–40`), underscoring that no approved production snapshot is supplied here.

**Impact.** Operators may believe the public register authorizes imports when it does not; alternatively they may create an ad-hoc compatible register, recreating the High allowlist-integrity problem.  This is fail-closed in the current command, so it is not a direct write bypass.

**Reproducible command and observed result.** This read-only command exited 2 during review with `import rejected: source register entry is missing source_id`:

```powershell
python -B backend-service/scripts/import_approved_course_artifact.py `
  --artifact docs/demo-data/open-data-source-register-v1.json `
  --source-register docs/demo-data/open-data-source-register-v1.json
```

**Remediation.** Define one authoritative versioned schema shared by documentation, importer, and source registry.  Include explicit approval status, immutable identifiers, usage policy, source allowlist, signer/provenance metadata, and the approved OER snapshot; do not silently translate ambiguous fields.

## Verified non-findings

- **Dry-run/apply boundary:** no database imports occur until after both input files are parsed, register matching completes, and artifact validation returns; dry-run exits with `writes=0` at `import_approved_course_artifact.py:265–278`.  `_apply()` is called only after both `--apply` and `--local-database` at lines 276–282.
- **Transaction/rollback:** database job creation, preview storage, and application are enclosed by `async with AsyncSessionLocal() as db, db.begin()` at `import_approved_course_artifact.py:233–244`.  The apply service relies on the caller transaction and creates courses as drafts (`is_published=False`) at `backend-service/app/services/content_agent_apply.py:161–182`; no automatic publication was found.
- **No direct network fetch in the reviewed adapter/importer:** the importer only calls local-path read APIs and the adapter only calls `read_bytes()`; neither imports an HTTP client.  This does not negate the generic validator/downloader regression documented above.
- **Executable markup/body prose handling:** `_OutlineHTMLParser` uses the non-executing standard-library `HTMLParser`, excludes script/iframe/audio/video/image/object/embed content (`oer_curriculum.py:157–176`), and applies `_plain_text()` to all extracted title and `data-oer-*` fields (`45–59, 221–260`), rejecting markup and control characters.  No execution or direct body-prose inclusion path was found in the adapter.
- **Output logging:** the importer prints a local artifact SHA-256, counts, and source checksums (`import_approved_course_artifact.py:271–283`) rather than input bodies, URLs, database URLs, or credentials.  The review did not find content/secret logging in this command; callers should still avoid putting secrets in paths because exception context outside this file may log command arguments.
- **Common Voice/deferred sources:** the demo register explicitly labels Common Voice deferred (`open-data-source-register-v1.json:8–18` and `.md:142–155`), and the new OER registry definition is disabled by default (`ai-service/api/services/content_etl/registry.py:170–180`).  The issue is enforcement at the separate importer boundary, captured in the first High finding, not a direct OER adapter reference to Common Voice.

## Commands run (no network, no database, no `.env` access)

```powershell
git status --short
rg --files -g 'AGENTS.md' -g 'import_approved_course_artifact.py' -g '*oer*' -g 'open-data-source-register-v1.*'
rg -n -C 4 "def validate_artifact|class ContentAgentApplyService|async def apply|source_manifest|publication|published|common_voice|deferred" backend-service/app ai-service/api/services/content_etl -g '*.py'
python -B -c "import ast, pathlib; paths=['backend-service/scripts/import_approved_course_artifact.py','ai-service/api/services/content_etl/adapters/oer_curriculum.py','ai-service/api/services/content_etl/contracts.py','ai-service/api/services/content_etl/registry.py','backend-service/app/schemas/content_agent.py']; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8'), filename=p) for p in paths]; print('AST syntax check passed for 5 reviewed Python modules')"
Push-Location ai-service; python -B -c "from api.services.content_etl.registry import validate_source_url; p=validate_source_url('oer_curriculum','https://example.invalid/arbitrary'); print(p.scheme, p.host, p.path)"; Pop-Location
python -B backend-service/scripts/import_approved_course_artifact.py --help
python -B backend-service/scripts/import_approved_course_artifact.py --artifact docs/demo-data/open-data-source-register-v1.json --source-register docs/demo-data/open-data-source-register-v1.json
git diff --check -- docs/demo-data/security-review-wave-c.md
```

The AST check passed.  The URL validation and register-contract commands produced the observed results recorded above; no request was sent by either command.
