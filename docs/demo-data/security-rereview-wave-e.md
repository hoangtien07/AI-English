# Security re-review — Wave E remediation

**Scope:** Wave C/E production changes and the canonical repository register. This was a read-only re-review: no network request, database connection, configuration edit, production edit, or test edit was made.

## Decision

**Blockers: 0. High findings: 0. Open Medium findings: 0. Mitigated Medium residuals: 1.**

DG-4's security condition **passes**: every prior High is closed, no new blocker or High was found, and the remaining local same-privilege race is documented below as mitigated rather than silently treated as closed. This conclusion assumes repository write access remains the intended trust root; a party able to modify the checked-in register is equivalent to a party able to modify the importer code.

## Disposition of Wave C findings

| Wave C finding | Current disposition | Current evidence |
|---|---|---|
| H1 — caller-controlled approval register / pins and deferred-source leakage | **Closed** | The parser no longer accepts `--source-register` at `backend-service/scripts/import_approved_course_artifact.py:243-248`; `main()` uses only the fixed `_REGISTER_PATH` at lines 16-23 and 254-257. The exact v2 register shape, four-ID allowlist, three approved IDs, and one specifically blocked OER ID are required at lines 127-156. Exact manifest pins and per-source usage allowlists are enforced at lines 173-191. The canonical register marks `oer_curriculum` blocked at `docs/demo-data/open-data-source-register-v1.json:46-56`, and the human-readable authority explains that Common Voice and other deferred sources cannot pass at `docs/demo-data/open-data-source-register-v1.md:3-12,22`. |
| H2 — OER provenance bypass and generic downloader | **Closed** | Registry URL validation requires HTTPS, no credentials/query/fragment, decoded canonical host/path rules at `ai-service/api/services/content_etl/registry.py:240-284`; the OER rule is exactly the LibreTexts host and path at lines 173-192. Contracts independently pin the same URL at `ai-service/api/services/content_etl/contracts.py:26-46,256-267,346-377`. `SecureDownloader.download()` rejects OER before it creates an HTTP client or validates a destination at `ai-service/api/services/content_etl/downloader.py:69-95`. |
| H3 — arbitrary SQLite target accepted by `--local-database` | **Closed** | `--apply` requires the development profile, rejects URI query/fragment ambiguity, permits only the exact resolved `backend-service/.local-dev/lexilingo-importer.sqlite3` path without a leaf symlink, or a loopback PostgreSQL URL with exact `lexilingo_dev` username/database identity at `backend-service/scripts/import_approved_course_artifact.py:208-224`. Application occurs only after this guard at lines 262-269. |
| M1 — symlink substitution / TOCTOU and no root boundary | **Mitigated** | Inputs must be repository-root descendants, regular `.json` files, and have no observed symlink components at `backend-service/scripts/import_approved_course_artifact.py:32-66`. The importer uses one `O_NOFOLLOW` final-file descriptor where supported, validates regular-file type and byte limit, reads/hashes one byte buffer, and compares pre/post descriptor identity/size at lines 92-115. Residual: the parent-component walk (40-48) and root resolution (51-66) happen before `os.open()` (95); a same-privilege attacker able to replace a parent directory in that interval can still redirect the later open on platforms without component-wise no-follow opens. This is not a remote path and requires local write/race capability. |
| M2 — unbounded JSON/HTML parsing | **Mitigated** | Importer limits artifact/register bytes at lines 19-21 and 92-115, then bounds JSON nesting, nodes, list entries, object keys, and string bytes at lines 69-90. The OER adapter limits snapshot size, record count, text, and scope entries at `ai-service/api/services/content_etl/adapters/oer_curriculum.py:46-49,58-85,243-304`. Residual: the adapter's `stat()` and later `read_bytes()` are separate at lines 307-320, so an attacker with filesystem race capability could replace a checked file with a larger one before the unrestricted read; 4 MiB is effective against ordinary inputs but not a fully atomic cap. No new High is warranted because this is local-only and needs that write/race capability. |
| M3 — published register/importer schema mismatch | **Closed** | The canonical JSON is schema version 2 with the exact keys expected by the importer (`docs/demo-data/open-data-source-register-v1.json:1-58`; importer lines 127-156). The documentation states the same schema and pin fields at `docs/demo-data/open-data-source-register-v1.md:3-12`. OER is consistently added to runtime enum/schema surfaces (`contracts.py:78-87`, `course-artifact-v2.schema.json:91-103`, and `source-record-v2.schema.json:33-45`), but it remains blocked by the importer register. |

## Re-tested controls and safe reproductions

All commands below are read-only with respect to production code, tests, configuration, the database, and the network. The downloader command exits before client construction, so the example URL is never requested.

```powershell
# From repository root: prove that no caller-controlled register option exists.
python -B backend-service/scripts/import_approved_course_artifact.py --help
python -B backend-service/scripts/import_approved_course_artifact.py `
  --artifact docs/demo-data/open-data-source-register-v1.json `
  --source-register docs/demo-data/open-data-source-register-v1.json
# Observed: argparse exits 2: unrecognized arguments: --source-register ...

# Canonical OER provenance succeeds; arbitrary provenance fails locally.
Push-Location ai-service
python -B -c "from api.services.content_etl.registry import validate_source_url; p=validate_source_url('oer_curriculum','https://human.libretexts.org/Courses/Evergreen_Valley_College/Listening_and_Speaking_for_Beginning_English_Language_Learners'); print('canonical=',p.host,p.path)"
python -B -c "from api.services.content_etl.registry import validate_source_url; validate_source_url('oer_curriculum','https://example.invalid/arbitrary')"
# Observed: canonical host/path printed; the second command exits nonzero with
# SourceRegistryError: Source URL is not approved for the canonical identity of oer_curriculum.

# This throws before an HTTP client is constructed or a request can be sent.
python -B -c "import asyncio; from api.services.content_etl.downloader import SecureDownloader; asyncio.run(SecureDownloader(storage=None,timeout_seconds=1,max_download_bytes=1,user_agent='review').download(source_name='oer_curriculum',version='x',url='https://example.invalid/x'))"
# Observed: command exits nonzero with DownloadSecurityError: OER curriculum snapshots are offline-only and cannot be downloaded.
Pop-Location

# Parse only; this does not import application settings or contact a database.
python -B -c "import ast,pathlib; paths=['backend-service/scripts/import_approved_course_artifact.py','ai-service/api/services/content_etl/adapters/oer_curriculum.py','ai-service/api/services/content_etl/contracts.py','ai-service/api/services/content_etl/registry.py','ai-service/api/services/content_etl/downloader.py']; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8'),filename=p) for p in paths]; print('AST syntax check passed')"
```

For the M1 residual, a safe non-exploit inspection is `rg -n "_no_symlink_components|resolve\(strict=True\)|os\.open\(|O_NOFOLLOW" backend-service/scripts/import_approved_course_artifact.py`: it shows validation at lines 40-66 and the later open at 92-107. Remediate by opening each path component from the trusted repository root with directory handles/no-follow semantics (or platform equivalent), retaining the descriptor through parse/hash/use, and add a controlled race test. For M2, use `rg -n "stat\(\)|read_bytes\(\)|MAX_SNAPSHOT_BYTES" ai-service/api/services/content_etl/adapters/oer_curriculum.py`; remediate by descriptor-based bounded reading with pre/post identity/size checks, matching the importer design.

## Additional verified non-findings

- **Strict local database identity:** no database was opened. The static guard cited above rejects non-development profiles, alternate SQLite paths, SQLite URI ambiguity, remote PostgreSQL hosts, non-default PostgreSQL ports, and non-`lexilingo_dev` identity.
- **Draft, transaction, and logging:** `_apply()` uses one `AsyncSessionLocal()` transaction at `backend-service/scripts/import_approved_course_artifact.py:227-240`; `ContentAgentApplyService` writes `is_published=False` at `backend-service/app/services/content_agent_apply.py:161-182`. Dry run prints `writes=0` at importer lines 260-264; output logs only the artifact digest, counts, raw checksums, IDs, and `draft=true` at lines 260-275—not bodies, database URLs, or credentials.
- **Schema compatibility:** the canonical register is fail-closed on exact root and entry key sets, rather than translating Wave C's old format. That removes the old approval ambiguity.

## Validation notes

`git diff --check` passed for tracked changes and an explicit no-index check passed for this untracked report. Targeted pytest was attempted with `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`, but it could not complete because the host denied pytest access to `C:\Users\hoang\AppData\Local\Temp\pytest-of-hoang` (`PermissionError: [WinError 5]`). Current Wave E test files cover the canonical-register, OER generic-downloader, checksum, size-limit, strict-local-database, draft, and symlink-rejection paths, but their pass/fail result is **not verified** in this host run.
