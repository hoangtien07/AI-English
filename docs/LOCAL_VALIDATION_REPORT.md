# Local validation report

## Scope and result

This report reconciles final local evidence collected on 2026-09-08. It
contains no credentials, environment values, container IDs, or remote
endpoints. No commit, push, deployment, account provisioning, scraping, or
destructive Git-history rewrite was performed.

| Area | Final result | Scope boundary |
|---|---|---|
| Independence | Sentinel passed; `git diff --check` passed. | Current deployable tree only; Git-history remediation/audit remains required before first push. |
| Compose | Configuration validation passed. | Configuration rendering, not a hosted deployment. |
| Backend | Focused: 17 passed; full isolated suite: 1679 passed, 3 skipped; Ruff passed. | Runner created/removed only a UUID-named `*_test` DB. API/service proof is not Flutter UI proof. |
| AI/STT | Clean image rebuilt; Moonshine wheel checksum OK; container healthy; 138 STT worker + 15 gate tests passed. | Real fixture returned non-empty output; about 1.4 s load, 1.2 s transcription, and 51,441,771-byte cache are observations, not a capacity benchmark. |
| Prior focused AI gates | Gemini chat/SSE, Piper TTS, HuBERT, and persistence gates passed. | Feature/service scope only; no complete voice-learning UI journey was exercised. |
| Admin | Build and tests passed. | Local build/test scope only. |
| Flutter | Focused config/Firebase: 5 passed; analysis: 13 warnings, no errors. | No full browser learner-journey acceptance evidence. |
| Data catalog | Manifest validation: 5 passed. | Validates references/statuses, not legal rights or publishability. |
| Developer experience | Pester: 9/9; actual `up-core`, `up-full`, and `status` passed. | Does not prove staging/production/hosting/mobile behavior. |

## Reproduction commands

Run from the repository root. These commands intentionally do not print secret
values; local commands require ignored, owner-supplied environment files.

```powershell
python scripts/security/verify_independent_config.py
git diff --check
docker compose -f docker-compose.dev.yml config --quiet
python -m pytest docs/tests/test_local_data_provenance_manifest.py -q

Push-Location backend-service
python -m scripts.run_isolated_tests
ruff check app scripts tests
Pop-Location

Push-Location flutter-app
flutter test test/core/network/api_config_environment_test.dart test/core/services/firebase_options_test.dart
flutter analyze --no-fatal-warnings --no-fatal-infos
Pop-Location

Invoke-Pester scripts/tests/DevLocal.Tests.ps1
.\scripts\dev-local.ps1 up-core
.\scripts\dev-local.ps1 up-full
.\scripts\dev-local.ps1 status
```

For the AI image, health, checksum, STT fixture smoke, and focused AI gates,
use the repository's documented local-STT commands and ignored local
environment values. Do not paste provider keys into shells, chat, logs, or
tracked files.

## Status-validation command

After changing the plan, validate that each original task ID appears once and
uses only the four final status values:

```powershell
@'
import re
from pathlib import Path
p = Path("docs/INDEPENDENT_DEVELOPMENT_PLAN.md")
text = p.read_text(encoding="utf-8")
ids = [f"L{wave}-{item:02d}" for wave, count in ((0, 6), (1, 7), (2, 8), (3, 8), (4, 9), (5, 7), (6, 7)) for item in range(1, count + 1)]
allowed = {"DONE", "SUPERSEDED", "BLOCKED", "NOT DONE"}
rows = re.findall(r"\| (L[0-6]-\d{2}) \| (DONE|SUPERSEDED|BLOCKED|NOT DONE) \|", text)
assert len(rows) == len(ids), (len(rows), len(ids))
assert {key for key, _ in rows} == set(ids)
assert len({key for key, _ in rows}) == len(ids)
assert {value for _, value in rows} <= allowed
print(f"validated {len(rows)} original IDs")
'@ | python -
```

## Open risks and decisions

- Choose local SMTP: Mailpit is recommended for capture-only local testing;
  alternatively use an owned Gmail App Password in an ignored file.
- Obtain owned Firebase app registration/configuration and necessary
  service-account details; confirm OAuth origins against those registrations.
- Approve an admin super-admin allowlist before enabling/admin-parity claims.
- Obtain source-by-source content rights approval before import, scraping, or
  publishing; public availability is not permission.
- Complete destructive Git-history remediation/audit before the first push.
- Rebrand, staging, production, hosting, and mobile delivery remain deferred.
