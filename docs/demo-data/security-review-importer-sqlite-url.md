# Final security re-review: approved-artifact importer database guard

Status: **PASS for applying the certified artifact to the dedicated local SQLite database**

Review date: 2026-09-12 (Asia/Saigon)

## Scope and method

Reviewed only:

- `backend-service/scripts/import_approved_course_artifact.py`
- `backend-service/tests/test_import_approved_course_artifact.py`
- this security report

The review independently checked the async SQLite exact-path guard and the PostgreSQL embedded-password remediation. Focused tests and safe in-process URL probes were run with a workspace-local temporary directory; no database connection or database mutation occurred, and no network access was used.

## Final findings

### Blocker: 0

No Blocker findings remain.

### High: 0

The prior High finding, H-1 (PostgreSQL embedded-password acceptance), is closed. At importer line 313, the PostgreSQL identity predicate now requires `parsed.password is None`, alongside the strict scheme, loopback host, port, username, and `/lexilingo_dev` path checks at lines 309-314. A direct safe probe rejected `postgresql+asyncpg://lexilingo_dev:pw@localhost/lexilingo_dev` and accepted the no-password loopback identity.

### Medium residuals: 2

**M-1 - SQLite database check-then-use residual.** Lines 287-306 resolve the expected path and check `candidate.is_symlink()` and `candidate.is_file()`; `_apply` then obtains the application engine at lines 319-322. A concurrent local actor able to replace the file or a parent directory after validation could race the later engine open. This is a residual local TOCTOU risk, not a blocker for the dedicated local apply under the stated local-development trust boundary. A stronger future mitigation would validate and hold an opened no-follow handle, or otherwise serialize/revalidate immediately before opening.

**M-2 - Source-file parent-component TOCTOU residual.** `_local_json_path` validates containment and components at lines 52-67, while `_read_json_bytes` opens later at lines 93-108. `O_NOFOLLOW` and inode/size checks protect the final file and detect some replacement, but a concurrent actor could still swap a parent directory between validation and open. This remains a medium local residual; it does not create a Blocker or High for this certified local apply. A stronger future mitigation would use trusted directory handles/no-follow traversal or require the staging root to be non-writable by untrusted concurrent users.

## Controls verified

- Development-only enforcement is explicit at lines 270-271 through `settings.is_development`.
- SQLite accepts only `sqlite` and `sqlite+aiosqlite`, rejects query/fragment and netloc/user/password ambiguity at lines 274-285, requires a drive-qualified forward-slash path at lines 288-299, and compares the resolved candidate with the hard-coded `.local-dev/lexilingo-importer.sqlite3` target at lines 287 and 300-306.
- The exact-path check rejects wrong, missing, symlink, UNC, backslash, relative, encoded-separator, extra-slash, query, and fragment forms.
- PostgreSQL accepts only the explicitly allowlisted loopback identity and rejects remote hosts, wrong ports/users/database paths, and embedded passwords at lines 308-314. Query and fragment rejection occurs before branch selection at lines 272-275.
- Artifact/register containment and no-symlink checks are at lines 33-67. Bounded JSON reads, regular-file checks, `O_NOFOLLOW` where available, and inode/size stability checks are at lines 93-108.

## Tests and probes

Focused command, run with a safe workspace-local temporary directory:

```powershell
$env:TEMP = (Join-Path (Get-Location) '.review-pytest-tmp-n5')
$env:TMP = $env:TEMP
$env:TMPDIR = $env:TEMP
Set-Location backend-service
python -m pytest tests/test_import_approved_course_artifact.py -q
```

Result: **77 passed in 1.19s**. Collection independently reported **77 tests collected**.

Relevant regression coverage is at tests lines 415-423 (both SQLite schemes and exact path), 438-480 (URI/netloc/UNC/backslash rejection), 483-552 (relative, wrong/missing, and symlink rejection), and 555-590 (PostgreSQL identity allow/deny cases). The embedded-password case was additionally exercised by the direct safe probe because the current parameterized PostgreSQL test list does not include a password-bearing URL.

Direct safe probe results (no engine import, connection, or DB write):

```text
sqlite exact: accept
sqlite wrong: reject
postgresql clean loopback: accept
postgresql embedded password: reject
postgresql remote host: reject
```

`git diff --check` completed without whitespace errors. Existing line-ending conversion warnings on unrelated dirty files were non-failing and outside this report-only change.

## Verdict

Finding count: **Blocker 0, High 0, Medium 2, Low 0**.

Final verdict: **PASS - the certified artifact may be applied to the dedicated local SQLite database**, provided the operator uses the exact development target `.local-dev/lexilingo-importer.sqlite3` and accepts the documented medium TOCTOU residuals. The prior High is closed; no Blocker or High remediation is required before this local apply.
