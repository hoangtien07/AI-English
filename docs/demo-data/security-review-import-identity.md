# Security review — import identity migration (Wave J2)

Scope was review-only: `content_agent.py`, `content_agent_jobs.py`, `import_approved_course_artifact.py`, and migration `c4e6a8f1b2d3`. No database, network, production code, tests, configuration, or environment files were modified. The review used static SQL/dialect reasoning and isolated syntax/pure-function checks only.

## Decision

**Blockers: 0. High findings: 0. Open Medium findings: 2. Low/informational compatibility notes: 1.**

**DG-4 security verdict: conditional fail for this scope.** Wave G High #1 is closed, but two medium operational/contract findings remain; DG-4 should not be marked passed until they are either fixed or explicitly accepted with tests and documented semantics.

## Wave G High #1 disposition

**Closed for duplicate completed imports.** The importer now derives a stable identity from a domain-separated, length-delimited SHA-256 construction at `backend-service/scripts/import_approved_course_artifact.py:232-267`; the database reserves non-NULL identities with a unique index at `backend-service/app/models/content_agent.py:89-100` and migration `c4e6a8f1b2d3_add_content_agent_import_identity.py:25-37`. `_apply()` creates/reserves, previews, and applies within one outer transaction at `backend-service/scripts/import_approved_course_artifact.py:289-316`; completed replay returns the stored job/course IDs at lines 303-308. Thus a second normal `--apply` cannot create a second completed job/course set for the same identity. The prior Wave G evidence at `docs/demo-data/code-review-wave-g.md:11-14` is superseded by this implementation.

## Findings

### M-01 — SQLite write-lock contention is not handled as a replay race

**Evidence:** `get_or_create_import_job()` performs an initial `with_for_update()` lookup and then relies on a nested-savepoint insert/`IntegrityError` path at `backend-service/app/services/content_agent_jobs.py:86-120`. SQLite does not implement row-level `FOR UPDATE`; concurrent writers contend on the database/file lock. The handler catches only `IntegrityError` at lines 110-119, not SQLite `OperationalError`/busy-lock errors. `_apply()` holds the same transaction across preview and all course/vocabulary writes at `backend-service/scripts/import_approved_course_artifact.py:299-316`, so a concurrent same-identity invocation may fail with a transient lock error rather than return `active`/`replayed`.

**Impact/rank:** Medium availability/reliability issue, constrained by the strict local-development database guard. PostgreSQL behavior is sound: a unique-index conflict waits for the winner and the post-savepoint lookup can observe the committed row; SQLite's coarse locking is not equivalent.

**Safe verification:**

```powershell
rg -n "with_for_update|begin_nested|IntegrityError|OperationalError|database is locked|busy_timeout" backend-service/app/services/content_agent_jobs.py backend-service/scripts/import_approved_course_artifact.py
```

**Remediation:** Add a SQLite-specific bounded busy/retry policy (or an explicit serialized import lock) around reservation/application, and test two concurrent same-identity calls against SQLite plus PostgreSQL. Preserve the unique index as the final authority; do not replace it with a check-then-insert only.

### M-02 — `--new-revision` is deterministic once, not a “next revision” allocator

**Evidence:** The base identity is transformed exactly once by the fixed revision domain separator at `backend-service/scripts/import_approved_course_artifact.py:263-266`. The CLI computes that identity at lines 339-352 and passes it to `_apply()` only when `--new-revision` is set. Repeating the same artifact with `--new-revision` therefore addresses the same alternate identity and returns `replayed`, not a fresh successive revision. The help text calls it “the explicit, deterministic next approved-import identity” at line 326, which is ambiguous against a user expectation that each explicit flag requests a new revision.

**Impact/rank:** Medium contract/compatibility issue. It does not reintroduce duplicate writes, but it can silently skip an operator-requested new import and makes revision behavior unlike the existing `ContentAgentJobService.create()` max-revision allocator at `backend-service/app/services/content_agent_jobs.py:123-163`.

**Remediation:** Specify one of these contracts and test it: (a) `--new-revision` means exactly one stable alternate revision and repeated use replays; rename/help-text it accordingly, or (b) allocate a monotonic revision under a transaction/lock and derive a distinct identity per revision. Do not use an unprotected `MAX(revision)+1` under concurrency.

## Replay/status, rollback, and compatibility review

| Case | Observed behavior | Verdict |
|---|---|---|
| Completed identity | Returns existing job and persisted course IDs, no writes (`import_approved_course_artifact.py:303-308`) | Safe/idempotent |
| Active identity | Returns existing job and no course IDs (`:309-310`) | Safe; caller can poll |
| Failed/cancelled identity | Raises conflict (`:311-313`); unique identity remains reserved | Safe against accidental duplicate, but no CLI retry path; compatibility note |
| New identity/apply failure | One `AsyncSession` plus `db.begin()` covers reservation, preview, and apply (`:299-316`); exception exits transaction and rolls back | Atomic, subject to underlying DB availability |
| Legacy rows | Nullable column and no backfill (`content_agent.py:61-65`; migration `:28-31`) preserve existing rows; unique indexes allow multiple NULLs on PostgreSQL and SQLite | Compatible |
| Migration downgrade | Drops unique index then column (`c4e6a8f1b2d3_add_content_agent_import_identity.py:40-45`) | Reversible for schema; identity data is intentionally lost on downgrade |

The failed/cancelled behavior is an informational compatibility note rather than a new High: it prevents silent duplicate content, and retry remains available through the existing job service (`content_agent_jobs.py:259-268`) if an operator has a job ID. The importer itself does not expose that recovery operation.

## Canonicalization, collision resistance, and leakage

- Identity input requires normalized lowercase 64-hex `generation_key` (`import_approved_course_artifact.py:235-237`) and normalized source-pin fields/checksums (`:238-250`).
- Artifact manifest order is canonicalized while preserving ordered course content (`:216-229`); pins are sorted by source name/snapshot (`:250`).
- Length-delimited fields and `lexilingo-approved-import-v1` provide framing/domain separation (`:251-262`); revision identities use a separate `lexilingo-approved-import-revision-v1` domain (`:263-266`). No practical SHA-256 collision or concatenation ambiguity was found in scope.
- The CLI prints artifact digest, import identity, raw checksums, job ID, and course IDs (`:339-360`) but not artifact bodies, credentials, or database URLs. Because `--apply` is restricted to the development profile and strict local/loopback database identity (`:270-287`), this is a local-operator information disclosure, not a new remote exposure. If shared logs are later introduced, redact identities/checksums or document them as sensitive metadata.

## Safe commands and evidence

```powershell
# Parse only; no settings import, DB connection, network, or writes.
python -B -c "import ast,pathlib; paths=['backend-service/app/models/content_agent.py','backend-service/app/services/content_agent_jobs.py','backend-service/scripts/import_approved_course_artifact.py','backend-service/alembic/versions/c4e6a8f1b2d3_add_content_agent_import_identity.py']; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8'),filename=p) for p in paths]; print('AST syntax check passed')"

# Review-only evidence search.
rg -n "import_identity|with_for_update|begin_nested|IntegrityError|new-revision|created_entity_ids|db\.begin\(" backend-service/app/models/content_agent.py backend-service/app/services/content_agent_jobs.py backend-service/scripts/import_approved_course_artifact.py backend-service/alembic/versions/c4e6a8f1b2d3_add_content_agent_import_identity.py

# Required whitespace check, including this untracked report.
git diff --check
git diff --no-index --check NUL docs/demo-data/security-review-import-identity.md
```

The graph/MCP commands named by `AGENTS.md` were not available in this dispatched shell; conclusions above are therefore based on exact file/line evidence and dialect-level static reasoning. No production or test edits were made.
